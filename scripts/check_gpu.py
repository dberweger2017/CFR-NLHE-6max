"""Check that PyTorch can train on this machine's accelerator, and measure it.

Reports the PyTorch build, the device it would use (CUDA, Apple MPS or CPU), and three
measurements: matrix-multiply throughput in float32 and float16, and training steps per
second for a small policy network of the size the neural-policy experiments start with.
Prints one JSON object. `--require cuda` (or `mps`) exits non-zero when that device isn't
usable, so setup scripts can check for it.

    python -m scripts.check_gpu
    python -m scripts.check_gpu --require cuda --quick
"""
import argparse
import json
import platform
import sys
import time


def device(torch):
    if torch.cuda.is_available():
        return torch.device('cuda')
    mps = getattr(torch.backends, 'mps', None)
    if mps is not None and mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


def sync(torch, dev):
    if dev.type == 'cuda':
        torch.cuda.synchronize()
    elif dev.type == 'mps':
        torch.mps.synchronize()


def timed(torch, dev, fn, repeats):
    fn()  # warm-up: kernel selection and allocation
    sync(torch, dev)
    start = time.perf_counter()
    for _ in range(repeats):
        fn()
    sync(torch, dev)
    return (time.perf_counter() - start) / repeats


def matmul_tflops(torch, dev, dtype, n, repeats):
    a = torch.randn(n, n, device=dev, dtype=dtype)
    b = torch.randn(n, n, device=dev, dtype=dtype)
    seconds = timed(torch, dev, lambda: a @ b, repeats)
    return 2 * n ** 3 / seconds / 1e12


def policy_steps(torch, dev, batch, width, inputs, actions, repeats):
    """Steps per second for a 4-layer MLP policy trained with cross-entropy to target strategies."""
    nn = torch.nn
    model = nn.Sequential(nn.Linear(inputs, width), nn.ReLU(), nn.Linear(width, width), nn.ReLU(),
                          nn.Linear(width, width), nn.ReLU(), nn.Linear(width, actions)).to(dev)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    x = torch.randn(batch, inputs, device=dev)
    target = torch.softmax(torch.randn(batch, actions, device=dev), dim=1)

    def step():
        optimizer.zero_grad(set_to_none=True)
        loss = -(target * torch.log_softmax(model(x), dim=1)).sum(dim=1).mean()
        loss.backward()
        optimizer.step()
    seconds = timed(torch, dev, step, repeats)
    parameters = sum(p.numel() for p in model.parameters())
    return {'steps_per_second': 1 / seconds, 'samples_per_second': batch / seconds,
            'batch': batch, 'width': width, 'parameters': parameters}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--require', choices=('cuda', 'mps'), help='exit 1 unless this device is usable')
    parser.add_argument('--quick', action='store_true', help='small sizes, for a fast setup check')
    args = parser.parse_args(argv)
    try:
        import torch
    except ImportError:
        print(json.dumps({'torch': None, 'error': 'PyTorch is not installed'}))
        return 1
    dev = device(torch)
    report = {'python': platform.python_version(), 'torch': torch.__version__,
              'cuda_build': torch.version.cuda, 'device': dev.type}
    if dev.type == 'cuda':
        p = torch.cuda.get_device_properties(0)
        report.update(name=p.name, memory_gb=round(p.total_memory / 2 ** 30, 2),
                      compute_capability=f'{p.major}.{p.minor}')
    n, repeats = (512, 3) if args.quick else (4096, 20)
    report['matmul_tflops'] = {'float32': round(matmul_tflops(torch, dev, torch.float32, n, repeats), 3)}
    if dev.type != 'cpu':
        report['matmul_tflops']['float16'] = round(matmul_tflops(torch, dev, torch.float16, n, repeats), 3)
    batch, width = (256, 128) if args.quick else (8192, 512)
    report['policy_mlp'] = policy_steps(torch, dev, batch, width, inputs=256, actions=6, repeats=repeats)
    print(json.dumps(report, indent=1))
    if args.require and dev.type != args.require:
        print(f'required device {args.require} is not usable (using {dev.type})', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
