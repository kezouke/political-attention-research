const fs=require('fs'),vm=require('vm'),path=require('path').resolve(__dirname,'../docs')+'/',html=fs.readFileSync(path+'index.html','utf8');
class E{constructor(tag){this.tag=tag;this.children=[];this.style={};this.events={};this.value='';this.dataset={};this.attrs={}}setAttribute(k,v){this.attrs[k]=v}replaceChildren(...x){this.children=x}append(...xs){this.children.push(...xs)}addEventListener(k,f){this.events[k]=f}}
let nodes={};for(const m of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g))nodes['#'+m[2]]=new E(m[1]);
nodes['#ess-select'].value='8';nodes['#spain-conditions-select'].value='unemploy';
let buttons=['en','ru'].map(v=>{let b=new E('button');b.dataset.setLanguage=v;return b});
const document={body:{dataset:{}},documentElement:{},querySelector(s){if(!nodes[s])throw Error('missing '+s);return nodes[s]},querySelectorAll(s){return s==='[data-set-language]'?buttons:[]},createElementNS(ns,t){return new E(t)},createElement(t){return new E(t)},createTextNode(t){let n=new E('text');n.textContent=t;return n}};
const c={window:{},document,location:{search:'',href:'https://example.com/'},history:{replaceState(){}},URL,URLSearchParams,console};vm.createContext(c);vm.runInContext(fs.readFileSync(path+'data.js','utf8'),c);vm.runInContext(fs.readFileSync(path+'app.js','utf8'),c);
const ids=['#cis-chart','#spain-conditions-chart','#brazil-chart','#common-shock-chart','#ess-chart'];
for(const id of ids){let svg=nodes[id].children.find(x=>x.tag==='svg');if(!svg||svg.children.length<10)throw Error('empty chart '+id)}
if(html.includes('id="appendix"'))throw Error('archived analysis should not appear on article page');
const brazil=nodes['#brazil-chart'].children.find(e=>e.tag==='svg');
if(brazil.children.filter(e=>e.tag==='rect').length!==10)throw Error('Brazil chart must show ten surveyed waves');
if(brazil.children.some(e=>e.tag==='polyline'||e.tag==='circle'))throw Error('Brazil chart must not interpolate unsurveyed years');
buttons[1].events.click();if(document.body.dataset.language!=='ru')throw Error('Russian switch failed');
buttons[0].events.click();if(document.body.dataset.language!=='en')throw Error('English switch failed');
nodes['#spain-conditions-select'].value='price';nodes['#spain-conditions-select'].events.change();
console.log('Five article charts, bilingual text, and sampled Brazil waves verified');
