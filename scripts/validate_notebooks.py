"""Execute all notebooks in a temporary copy; preserve source data and notebook edits."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def validate():
    originals = list((ROOT / 'notebooks').glob('*.ipynb')) + list((ROOT / 'data').rglob('*.json'))
    hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
    old_env = {key: os.environ.get(key) for key in ['JUPYTER_PATH', 'PYTHONPATH', 'IPYTHONDIR', 'MPLCONFIGDIR']}
    try:
        with tempfile.TemporaryDirectory(prefix='tripgenie-notebooks-') as temporary:
            work = Path(temporary)
            shutil.copytree(ROOT / 'data', work / 'data')
            (work / 'notebooks').mkdir()
            kernel_dir = work / 'jupyter/kernels/tripgenie-validate'
            kernel_dir.mkdir(parents=True)
            (kernel_dir / 'kernel.json').write_text(json.dumps({
                'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
                'display_name': 'TripGenie validation', 'language': 'python'}))
            os.environ.update(JUPYTER_PATH=str(work / 'jupyter'), PYTHONPATH=str(ROOT),
                              IPYTHONDIR=str(work / 'ipython'), MPLCONFIGDIR=str(work / 'matplotlib'))
            for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
                notebook = nbformat.read(path, as_version=4)
                NotebookClient(notebook, timeout=180, kernel_name='tripgenie-validate',
                               resources={'metadata': {'path': str(work / 'notebooks')}}).execute()
                cells = [c for c in notebook.cells if c.cell_type == 'code']
                assert [c.execution_count for c in cells] == list(range(1, len(cells) + 1))
                assert not any(o.output_type == 'error' for c in cells for o in c.outputs)
                print(f'{path.name}: {len(cells)} code cells passed', flush=True)
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    assert hashes == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
    print('All original notebooks and dataset files are unchanged.')


if __name__ == '__main__':
    validate()
