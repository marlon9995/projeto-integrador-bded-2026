"""Gera copia de seguranca e manifesto dos arquivos versionados."""
import hashlib,json,subprocess,zipfile
from src.collect import ROOT
def package():
    output=ROOT/'dist';output.mkdir(exist_ok=True)
    raw=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT)
    names=[n.decode('utf-8') for n in raw.split(b'\0') if n]
    manifest={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    (output/'manifesto_sha256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive=output/'Projeto_Integrador_P15.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(ROOT/n,'projeto_integrador/'+n)
        z.write(output/'manifesto_sha256.json','projeto_integrador/manifesto_sha256.json')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read('projeto_integrador/'+n)).hexdigest()==h for n,h in manifest.items())
    print('ZIP e hashes verificados:',len(names),'arquivos')
if __name__=='__main__':package()
