"""Executa células sequencialmente no processo atual, sem sockets de kernel."""
from pathlib import Path
import contextlib,io,os
import nbformat
from IPython.core.interactiveshell import InteractiveShell
root=Path(__file__).resolve().parents[1]
os.chdir(root)
p=root/'notebooks/01_launchlens_end_to_end.ipynb'
nb=nbformat.read(p,as_version=4)
shell=InteractiveShell.instance()
for count,cell in enumerate((c for c in nb.cells if c.cell_type=='code'),1):
    outputs=[]
    def publish(data,metadata=None,**kwargs):
        outputs.append(nbformat.v4.new_output('display_data',data=data,metadata=metadata or {}))
    shell.display_pub.publish=publish
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf),contextlib.redirect_stderr(buf):
        result=shell.run_cell(cell.source,store_history=False)
    if result.error_before_exec or result.error_in_exec:
        raise RuntimeError(buf.getvalue())
    if buf.getvalue():outputs.insert(0,nbformat.v4.new_output('stream',name='stdout',text=buf.getvalue()))
    cell.outputs=outputs;cell.execution_count=count
nbformat.write(nb,p)
print('Notebook executado: todas as células, sem erros (IPython no processo atual).')
