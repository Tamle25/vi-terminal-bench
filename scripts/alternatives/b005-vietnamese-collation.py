import subprocess

SCRIPT=r'''
const fs=require('fs'),root=process.argv[1];
const input=JSON.parse(fs.readFileSync(root+'/data/catalog.json','utf8'));
const compare=new Intl.Collator('vi',{usage:'sort',sensitivity:'variant',caseFirst:'lower',numeric:false,ignorePunctuation:false}).compare;
const output=[];
for(const row of input){
 let index=0;
 while(index<output.length){
  const other=output[index];
  const relation=compare(row.name.normalize('NFC'),other.name.normalize('NFC'));
  if(relation<0 || (relation===0 && row.id<other.id))break;
  index++;
 }
 output.splice(index,0,{name:row.name,id:row.id});
}
fs.mkdirSync(root+'/output',{recursive:true});
fs.writeFileSync(root+'/output/catalog.json',JSON.stringify(output,null,2));
'''


def solve(root):
    subprocess.run(['node','-e',SCRIPT,str(root)],check=True)
