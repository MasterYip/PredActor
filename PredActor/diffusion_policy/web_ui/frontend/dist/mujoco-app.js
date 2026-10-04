const Um="modulepreload",Nm=function(r){return"/wasm/"+r},Fc={},Om=function(e,t,n){let a=Promise.resolve();if(t&&t.length>0){let p=function(f){return Promise.all(f.map(_=>Promise.resolve(_).then(v=>({status:"fulfilled",value:v}),v=>({status:"rejected",reason:v}))))};document.getElementsByTagName("link");const l=document.querySelector("meta[property=csp-nonce]"),u=l?.nonce||l?.getAttribute("nonce");a=p(t.map(f=>{if(f=Nm(f),f in Fc)return;Fc[f]=!0;const _=f.endsWith(".css"),v=_?'[rel="stylesheet"]':"";if(document.querySelector(`link[href="${f}"]${v}`))return;const x=document.createElement("link");if(x.rel=_?"stylesheet":Um,_||(x.as="script"),x.crossOrigin="",x.href=f,u&&x.setAttribute("nonce",u),document.head.appendChild(x),_)return new Promise((E,R)=>{x.addEventListener("load",E),x.addEventListener("error",()=>R(new Error(`Unable to preload CSS for ${f}`)))})}))}function o(l){const u=new Event("vite:preloadError",{cancelable:!0});if(u.payload=l,window.dispatchEvent(u),!u.defaultPrevented)throw l}return a.then(l=>{for(const u of l||[])u.status==="rejected"&&o(u.reason);return e().catch(o)})};var km=(async function(r={}){var e,t=r,n=typeof window=="object",a=typeof WorkerGlobalScope<"u",o=typeof process=="object"&&process.versions?.node&&process.type!="renderer",l=!n&&!o&&!a;if(o){const{createRequire:i}=await Om(async()=>{const{createRequire:s}=await Promise.resolve().then(()=>ME);return{createRequire:s}},void 0);var u=i(import.meta.url)}var p="./this.program",f=(i,s)=>{throw s},_=import.meta.url,v="";function x(i){return t.locateFile?t.locateFile(i,v):v+i}var E,R;if(o){if(!(typeof process=="object"&&process.versions?.node&&process.type!="renderer"))throw new Error("not compiled for this environment (did you build to HTML and try to run it not on the web, or set ENVIRONMENT to something - like node - and run it someplace else - like on the web?)");var C=process.versions.node,y=C.split(".").slice(0,3);if(y=y[0]*1e4+y[1]*100+y[2].split("-")[0]*1,y<16e4)throw new Error("This emscripten-generated code requires node v16.0.0 (detected v"+C+")");var m=u("fs");_.startsWith("file:")&&(v=u("path").dirname(u("url").fileURLToPath(_))+"/"),R=s=>{s=H(s)?new URL(s):s;var c=m.readFileSync(s);return D(Buffer.isBuffer(c)),c},E=async(s,c=!0)=>{s=H(s)?new URL(s):s;var h=m.readFileSync(s,c?void 0:"utf8");return D(c?Buffer.isBuffer(h):typeof h=="string"),h},process.argv.length>1&&(p=process.argv[1].replace(/\\/g,"/")),process.argv.slice(2),f=(s,c)=>{throw process.exitCode=s,c}}else if(l){if(typeof process=="object"&&process.versions?.node&&process.type!="renderer"||typeof window=="object"||typeof WorkerGlobalScope<"u")throw new Error("not compiled for this environment (did you build to HTML and try to run it not on the web, or set ENVIRONMENT to something - like node - and run it someplace else - like on the web?)")}else if(n||a){try{v=new URL(".",_).href}catch{}if(!(typeof window=="object"||typeof WorkerGlobalScope<"u"))throw new Error("not compiled for this environment (did you build to HTML and try to run it not on the web, or set ENVIRONMENT to something - like node - and run it someplace else - like on the web?)");a&&(R=i=>{var s=new XMLHttpRequest;return s.open("GET",i,!1),s.responseType="arraybuffer",s.send(null),new Uint8Array(s.response)}),E=async i=>{if(H(i))return new Promise((c,h)=>{var d=new XMLHttpRequest;d.open("GET",i,!0),d.responseType="arraybuffer",d.onload=()=>{if(d.status==200||d.status==0&&d.response){c(d.response);return}h(d.status)},d.onerror=h,d.send(null)});var s=await fetch(i,{credentials:"same-origin"});if(s.ok)return s.arrayBuffer();throw new Error(s.status+" : "+s.url)}}else throw new Error("environment detection error");var N=console.log.bind(console),I=console.error.bind(console);D(!l,"shell environment detected but not enabled at build time.  Add `shell` to `-sENVIRONMENT` to enable.");var L;typeof WebAssembly!="object"&&I("no native wasm support detected");var B=!1;function D(i,s){i||Y("Assertion failed"+(s?": "+s:""))}var H=i=>i.startsWith("file://");function q(){var i=ta();D((i&3)==0),i==0&&(i+=4),ve[i>>2]=34821223,ve[i+4>>2]=2310721022,ve[0]=1668509029}function P(){if(!B){var i=ta();i==0&&(i+=4);var s=ve[i>>2],c=ve[i+4>>2];(s!=34821223||c!=2310721022)&&Y(`Stack overflow! Stack cookie has been overwritten at ${Ie(i)}, expected hex dwords 0x89BACDFE and 0x2135467, but received ${Ie(c)} ${Ie(s)}`),ve[0]!=1668509029&&Y("Runtime error: The application has corrupted its heap memory area (address zero)!")}}class M extends Error{}class O extends M{}class te extends M{constructor(s){super(s),this.excPtr=s;const c=xc(s);this.name=c[0],this.message=c[1]}}(()=>{var i=new Int16Array(1),s=new Int8Array(i.buffer);if(i[0]=25459,s[0]!==115||s[1]!==99)throw"Runtime error: expected the system to be little-endian! (Run with -sSUPPORT_BIG_ENDIAN to bypass)"})();function ee(i){Object.getOwnPropertyDescriptor(t,i)||Object.defineProperty(t,i,{configurable:!0,set(){Y(`Attempt to set \`Module.${i}\` after it has already been processed.  This can happen, for example, when code is injected via '--post-js' rather than '--pre-js'`)}})}function Z(i){return()=>D(!1,`call to '${i}' via reference taken before Wasm module initialization`)}function he(i){Object.getOwnPropertyDescriptor(t,i)&&Y(`\`Module.${i}\` was supplied but \`${i}\` not included in INCOMING_MODULE_JS_API`)}function ae(i){return i==="FS_createPath"||i==="FS_createDataFile"||i==="FS_createPreloadedFile"||i==="FS_unlink"||i==="addRunDependency"||i==="FS_createLazyFile"||i==="FS_createDevice"||i==="removeRunDependency"}function Se(i,s){typeof globalThis<"u"&&!Object.getOwnPropertyDescriptor(globalThis,i)&&Object.defineProperty(globalThis,i,{configurable:!0,get(){s()}})}function re(i,s){Se(i,()=>{Fe(`\`${i}\` is not longer defined by emscripten. ${s}`)})}re("buffer","Please use HEAP8.buffer or wasmMemory.buffer"),re("asm","Please use wasmExports instead");function Ae(i){Se(i,()=>{var s=`\`${i}\` is a library symbol and not included by default; add it to your library.js __deps or to DEFAULT_LIBRARY_FUNCS_TO_INCLUDE on the command line`,c=i;c.startsWith("_")||(c="$"+i),s+=` (e.g. -sDEFAULT_LIBRARY_FUNCS_TO_INCLUDE='${c}')`,ae(i)&&(s+=". Alternatively, forcing filesystem support (-sFORCE_FILESYSTEM) can export this for you"),Fe(s)}),De(i)}function De(i){Object.getOwnPropertyDescriptor(t,i)||Object.defineProperty(t,i,{configurable:!0,get(){var s=`'${i}' was not exported. add it to EXPORTED_RUNTIME_METHODS (see the Emscripten FAQ)`;ae(i)&&(s+=". Alternatively, forcing filesystem support (-sFORCE_FILESYSTEM) can export this for you"),Y(s)}})}var Ve,tt,xt,Ze,ie,Te,Ee,ue,ve,Ye,Ct,Qe,k,_t=!1;function We(){var i=xt.buffer;Ze=new Int8Array(i),Te=new Int16Array(i),ie=new Uint8Array(i),Ee=new Uint16Array(i),ue=new Int32Array(i),ve=new Uint32Array(i),Ye=new Float32Array(i),Ct=new Float64Array(i),Qe=new BigInt64Array(i),k=new BigUint64Array(i)}D(typeof Int32Array<"u"&&typeof Float64Array<"u"&&Int32Array.prototype.subarray!=null&&Int32Array.prototype.set!=null,"JS engine does not provide full typed array support");function ft(){if(t.preRun)for(typeof t.preRun=="function"&&(t.preRun=[t.preRun]);t.preRun.length;)ye(t.preRun.shift());ee("preRun"),ke(V)}function Ge(){D(!_t),_t=!0,P(),!t.noFSInit&&!S.initialized&&S.init(),mi.__wasm_call_ctors(),S.ignorePermissions=!1}function At(){if(P(),t.postRun)for(typeof t.postRun=="function"&&(t.postRun=[t.postRun]);t.postRun.length;)nt(t.postRun.shift());ee("postRun"),ke(we)}var Le=0,Je=null,Pt={},Et=null;function U(i){Le++,t.monitorRunDependencies?.(Le),i?(D(!Pt[i]),Pt[i]=1,Et===null&&typeof setInterval<"u"&&(Et=setInterval(()=>{if(B){clearInterval(Et),Et=null;return}var s=!1;for(var c in Pt)s||(s=!0,I("still waiting on run dependencies:")),I(`dependency: ${c}`);s&&I("(end of list)")},1e4))):I("warning: run dependency added without ID")}function w(i){if(Le--,t.monitorRunDependencies?.(Le),i?(D(Pt[i]),delete Pt[i]):I("warning: run dependency removed without ID"),Le==0&&(Et!==null&&(clearInterval(Et),Et=null),Je)){var s=Je;Je=null,s()}}function Y(i){t.onAbort?.(i),i="Aborted("+i+")",I(i),B=!0;var s=new WebAssembly.RuntimeError(i);throw tt?.(s),s}function ne(i,s){return(...c)=>{D(_t,`native function \`${i}\` called before runtime initialization`);var h=mi[i];return D(h,`exported native function \`${i}\` not found`),D(c.length<=s,`native function \`${i}\` called with ${c.length} args but expects ${s}`),h(...c)}}var de;function se(){return t.locateFile?x("mujoco.wasm"):new URL("/wasm/assets/mujoco-Bp43jdDU.wasm",import.meta.url).href}function ze(i){if(i==de&&L)return new Uint8Array(L);if(R)return R(i);throw"both async and sync fetching of the wasm failed"}async function Me(i){if(!L)try{var s=await E(i);return new Uint8Array(s)}catch{}return ze(i)}async function Oe(i,s){try{var c=await Me(i),h=await WebAssembly.instantiate(c,s);return h}catch(d){I(`failed to asynchronously prepare wasm: ${d}`),H(de)&&I(`warning: Loading from a file URI (${de}) is not supported in most browsers. See https://emscripten.org/docs/getting_started/FAQ.html#how-do-i-run-a-local-webserver-for-testing-why-does-my-program-stall-in-downloading-or-preparing`),Y(d)}}async function Be(i,s,c){if(!i&&typeof WebAssembly.instantiateStreaming=="function"&&!H(s)&&!o)try{var h=fetch(s,{credentials:"same-origin"}),d=await WebAssembly.instantiateStreaming(h,c);return d}catch(g){I(`wasm streaming compile failed: ${g}`),I("falling back to ArrayBuffer instantiation")}return Oe(s,c)}function xe(){return{env:Dc,wasi_snapshot_preview1:Dc}}async function Pe(){function i(T,b){return mi=T.exports,xt=mi.memory,D(xt,"memory not found in wasm exports"),We(),Vr=mi.__indirect_function_table,D(Vr,"table not found in wasm exports"),Nd(mi),w("wasm-instantiate"),mi}U("wasm-instantiate");var s=t;function c(T){return D(t===s,"the Module object should not be replaced during async compilation - perhaps the order of HTML elements is wrong?"),s=null,i(T.instance)}var h=xe();if(t.instantiateWasm)return new Promise((T,b)=>{try{t.instantiateWasm(h,(F,W)=>{T(i(F,W))})}catch(F){I(`Module.instantiateWasm callback failed with error: ${F}`),b(F)}});de??=se();var d=await Be(L,de,h),g=c(d);return g}class $e{name="ExitStatus";constructor(s){this.message=`Program terminated with exit(${s})`,this.status=s}}var ke=i=>{for(;i.length>0;)i.shift()(t)},we=[],nt=i=>we.push(i),V=[],ye=i=>V.push(i),be=!0,Ie=i=>(D(typeof i=="number"),i>>>=0,"0x"+i.toString(16).padStart(8,"0")),G=i=>bc(i),z=()=>Ac(),Fe=i=>{Fe.shown||={},Fe.shown[i]||(Fe.shown[i]=1,o&&(i="warning: "+i),I(i))},Ke=typeof TextDecoder<"u"?new TextDecoder:void 0,pt=(i,s=0,c=NaN)=>{for(var h=s+c,d=s;i[d]&&!(d>=h);)++d;if(d-s>16&&i.buffer&&Ke)return Ke.decode(i.subarray(s,d));for(var g="";s<d;){var T=i[s++];if(!(T&128)){g+=String.fromCharCode(T);continue}var b=i[s++]&63;if((T&224)==192){g+=String.fromCharCode((T&31)<<6|b);continue}var F=i[s++]&63;if((T&240)==224?T=(T&15)<<12|b<<6|F:((T&248)!=240&&Fe("Invalid UTF-8 leading byte "+Ie(T)+" encountered when deserializing a UTF-8 string in wasm memory to a JS string!"),T=(T&7)<<18|b<<12|F<<6|i[s++]&63),T<65536)g+=String.fromCharCode(T);else{var W=T-65536;g+=String.fromCharCode(55296|W>>10,56320|W&1023)}}return g},rt=(i,s)=>(D(typeof i=="number",`UTF8ToString expects a number (got ${typeof i})`),i?pt(ie,i,s):""),gn=(i,s,c,h)=>Y(`Assertion failed: ${rt(i)}, at: `+[s?rt(s):"unknown filename",c,h?rt(h):"unknown function"]),Ot=[],li=0,Un=i=>{var s=new Nn(i);return s.get_caught()||(s.set_caught(!0),li--),s.set_rethrown(!1),Ot.push(s),Yr(i),Pc(i)},cr=()=>{if(!Ot.length)return 0;var i=Ot[Ot.length-1];return Yr(i.excPtr),i.excPtr},dn=0,Pr=()=>{me(0,0),D(Ot.length>0);var i=Ot.pop();na(i.excPtr),dn=0};class Nn{constructor(s){this.excPtr=s,this.ptr=s-24}set_type(s){ve[this.ptr+4>>2]=s}get_type(){return ve[this.ptr+4>>2]}set_destructor(s){ve[this.ptr+8>>2]=s}get_destructor(){return ve[this.ptr+8>>2]}set_caught(s){s=s?1:0,Ze[this.ptr+12]=s}get_caught(){return Ze[this.ptr+12]!=0}set_rethrown(s){s=s?1:0,Ze[this.ptr+13]=s}get_rethrown(){return Ze[this.ptr+13]!=0}init(s,c){this.set_adjusted_ptr(0),this.set_type(s),this.set_destructor(c)}set_adjusted_ptr(s){ve[this.ptr+16>>2]=s}get_adjusted_ptr(){return ve[this.ptr+16>>2]}}var ui=i=>Mc(i),qn=i=>{var s=dn?.excPtr;if(!s)return ui(0),0;var c=new Nn(s);c.set_adjusted_ptr(s);var h=c.get_type();if(!h)return ui(0),s;for(var d of i){if(d===0||d===h)break;var g=c.ptr+16;if(Cc(d,h,g))return ui(d),s}return ui(h),s},Dr=()=>qn([]),Lr=i=>qn([i]),Bs=(i,s)=>qn([i,s]),Ir=()=>{var i=Ot.pop();i||Y("no exception to throw");var s=i.excPtr;throw i.get_rethrown()||(Ot.push(i),i.set_rethrown(!0),i.set_caught(!1),li++),dn=new te(s),dn},zs=i=>{if(i){var s=new Nn(i);Ot.push(s),s.set_rethrown(!0),Ir()}},Hs=(i,s,c)=>{var h=new Nn(i);throw h.init(s,c),dn=new te(i),li++,dn},Vs=()=>li,Gs=i=>{throw dn||(dn=new te(i)),dn},A={isAbs:i=>i.charAt(0)==="/",splitPath:i=>{var s=/^(\/?|)([\s\S]*?)((?:\.{1,2}|[^\/]+?|)(\.[^.\/]*|))(?:[\/]*)$/;return s.exec(i).slice(1)},normalizeArray:(i,s)=>{for(var c=0,h=i.length-1;h>=0;h--){var d=i[h];d==="."?i.splice(h,1):d===".."?(i.splice(h,1),c++):c&&(i.splice(h,1),c--)}if(s)for(;c;c--)i.unshift("..");return i},normalize:i=>{var s=A.isAbs(i),c=i.slice(-1)==="/";return i=A.normalizeArray(i.split("/").filter(h=>!!h),!s).join("/"),!i&&!s&&(i="."),i&&c&&(i+="/"),(s?"/":"")+i},dirname:i=>{var s=A.splitPath(i),c=s[0],h=s[1];return!c&&!h?".":(h&&(h=h.slice(0,-1)),c+h)},basename:i=>i&&i.match(/([^\/]+|\/)\/*$/)[1],join:(...i)=>A.normalize(i.join("/")),join2:(i,s)=>A.normalize(i+"/"+s)},j=()=>{if(o){var i=u("crypto");return s=>i.randomFillSync(s)}return s=>crypto.getRandomValues(s)},Q=i=>{(Q=j())(i)},J={resolve:(...i)=>{for(var s="",c=!1,h=i.length-1;h>=-1&&!c;h--){var d=h>=0?i[h]:S.cwd();if(typeof d!="string")throw new TypeError("Arguments to path.resolve must be strings");if(!d)return"";s=d+"/"+s,c=A.isAbs(d)}return s=A.normalizeArray(s.split("/").filter(g=>!!g),!c).join("/"),(c?"/":"")+s||"."},relative:(i,s)=>{i=J.resolve(i).slice(1),s=J.resolve(s).slice(1);function c(W){for(var K=0;K<W.length&&W[K]==="";K++);for(var oe=W.length-1;oe>=0&&W[oe]==="";oe--);return K>oe?[]:W.slice(K,oe-K+1)}for(var h=c(i.split("/")),d=c(s.split("/")),g=Math.min(h.length,d.length),T=g,b=0;b<g;b++)if(h[b]!==d[b]){T=b;break}for(var F=[],b=T;b<h.length;b++)F.push("..");return F=F.concat(d.slice(T)),F.join("/")}},$=[],pe=i=>{for(var s=0,c=0;c<i.length;++c){var h=i.charCodeAt(c);h<=127?s++:h<=2047?s+=2:h>=55296&&h<=57343?(s+=4,++c):s+=3}return s},Re=(i,s,c,h)=>{if(D(typeof i=="string",`stringToUTF8Array expects a string (got ${typeof i})`),!(h>0))return 0;for(var d=c,g=c+h-1,T=0;T<i.length;++T){var b=i.codePointAt(T);if(b<=127){if(c>=g)break;s[c++]=b}else if(b<=2047){if(c+1>=g)break;s[c++]=192|b>>6,s[c++]=128|b&63}else if(b<=65535){if(c+2>=g)break;s[c++]=224|b>>12,s[c++]=128|b>>6&63,s[c++]=128|b&63}else{if(c+3>=g)break;b>1114111&&Fe("Invalid Unicode code point "+Ie(b)+" encountered when serializing a JS string to a UTF-8 string in wasm memory! (Valid unicode code points should be in range 0-0x10FFFF)."),s[c++]=240|b>>18,s[c++]=128|b>>12&63,s[c++]=128|b>>6&63,s[c++]=128|b&63,T++}}return s[c]=0,c-d},Ne=(i,s,c)=>{var h=pe(i)+1,d=new Array(h),g=Re(i,d,0,d.length);return d.length=g,d},Ue=()=>{if(!$.length){var i=null;if(o){var s=256,c=Buffer.alloc(s),h=0,d=process.stdin.fd;try{h=m.readSync(d,c,0,s)}catch(g){if(g.toString().includes("EOF"))h=0;else throw g}h>0&&(i=c.slice(0,h).toString("utf-8"))}else typeof window<"u"&&typeof window.prompt=="function"&&(i=window.prompt("Input: "),i!==null&&(i+=`
`));if(!i)return null;$=Ne(i)}return $.shift()},He={ttys:[],init(){},shutdown(){},register(i,s){He.ttys[i]={input:[],output:[],ops:s},S.registerDevice(i,He.stream_ops)},stream_ops:{open(i){var s=He.ttys[i.node.rdev];if(!s)throw new S.ErrnoError(43);i.tty=s,i.seekable=!1},close(i){i.tty.ops.fsync(i.tty)},fsync(i){i.tty.ops.fsync(i.tty)},read(i,s,c,h,d){if(!i.tty||!i.tty.ops.get_char)throw new S.ErrnoError(60);for(var g=0,T=0;T<h;T++){var b;try{b=i.tty.ops.get_char(i.tty)}catch{throw new S.ErrnoError(29)}if(b===void 0&&g===0)throw new S.ErrnoError(6);if(b==null)break;g++,s[c+T]=b}return g&&(i.node.atime=Date.now()),g},write(i,s,c,h,d){if(!i.tty||!i.tty.ops.put_char)throw new S.ErrnoError(60);try{for(var g=0;g<h;g++)i.tty.ops.put_char(i.tty,s[c+g])}catch{throw new S.ErrnoError(29)}return h&&(i.node.mtime=i.node.ctime=Date.now()),g}},default_tty_ops:{get_char(i){return Ue()},put_char(i,s){s===null||s===10?(N(pt(i.output)),i.output=[]):s!=0&&i.output.push(s)},fsync(i){i.output?.length>0&&(N(pt(i.output)),i.output=[])},ioctl_tcgets(i){return{c_iflag:25856,c_oflag:5,c_cflag:191,c_lflag:35387,c_cc:[3,28,127,21,4,0,1,0,17,19,26,0,18,15,23,22,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]}},ioctl_tcsets(i,s,c){return 0},ioctl_tiocgwinsz(i){return[24,80]}},default_tty1_ops:{put_char(i,s){s===null||s===10?(I(pt(i.output)),i.output=[]):s!=0&&i.output.push(s)},fsync(i){i.output?.length>0&&(I(pt(i.output)),i.output=[])}}},qe=i=>{Y("internal error: mmapAlloc called but `emscripten_builtin_memalign` native symbol not exported")},_e={ops_table:null,mount(i){return _e.createNode(null,"/",16895,0)},createNode(i,s,c,h){if(S.isBlkdev(c)||S.isFIFO(c))throw new S.ErrnoError(63);_e.ops_table||={dir:{node:{getattr:_e.node_ops.getattr,setattr:_e.node_ops.setattr,lookup:_e.node_ops.lookup,mknod:_e.node_ops.mknod,rename:_e.node_ops.rename,unlink:_e.node_ops.unlink,rmdir:_e.node_ops.rmdir,readdir:_e.node_ops.readdir,symlink:_e.node_ops.symlink},stream:{llseek:_e.stream_ops.llseek}},file:{node:{getattr:_e.node_ops.getattr,setattr:_e.node_ops.setattr},stream:{llseek:_e.stream_ops.llseek,read:_e.stream_ops.read,write:_e.stream_ops.write,mmap:_e.stream_ops.mmap,msync:_e.stream_ops.msync}},link:{node:{getattr:_e.node_ops.getattr,setattr:_e.node_ops.setattr,readlink:_e.node_ops.readlink},stream:{}},chrdev:{node:{getattr:_e.node_ops.getattr,setattr:_e.node_ops.setattr},stream:S.chrdev_stream_ops}};var d=S.createNode(i,s,c,h);return S.isDir(d.mode)?(d.node_ops=_e.ops_table.dir.node,d.stream_ops=_e.ops_table.dir.stream,d.contents={}):S.isFile(d.mode)?(d.node_ops=_e.ops_table.file.node,d.stream_ops=_e.ops_table.file.stream,d.usedBytes=0,d.contents=null):S.isLink(d.mode)?(d.node_ops=_e.ops_table.link.node,d.stream_ops=_e.ops_table.link.stream):S.isChrdev(d.mode)&&(d.node_ops=_e.ops_table.chrdev.node,d.stream_ops=_e.ops_table.chrdev.stream),d.atime=d.mtime=d.ctime=Date.now(),i&&(i.contents[s]=d,i.atime=i.mtime=i.ctime=d.atime),d},getFileDataAsTypedArray(i){return i.contents?i.contents.subarray?i.contents.subarray(0,i.usedBytes):new Uint8Array(i.contents):new Uint8Array(0)},expandFileStorage(i,s){var c=i.contents?i.contents.length:0;if(!(c>=s)){var h=1024*1024;s=Math.max(s,c*(c<h?2:1.125)>>>0),c!=0&&(s=Math.max(s,256));var d=i.contents;i.contents=new Uint8Array(s),i.usedBytes>0&&i.contents.set(d.subarray(0,i.usedBytes),0)}},resizeFileStorage(i,s){if(i.usedBytes!=s)if(s==0)i.contents=null,i.usedBytes=0;else{var c=i.contents;i.contents=new Uint8Array(s),c&&i.contents.set(c.subarray(0,Math.min(s,i.usedBytes))),i.usedBytes=s}},node_ops:{getattr(i){var s={};return s.dev=S.isChrdev(i.mode)?i.id:1,s.ino=i.id,s.mode=i.mode,s.nlink=1,s.uid=0,s.gid=0,s.rdev=i.rdev,S.isDir(i.mode)?s.size=4096:S.isFile(i.mode)?s.size=i.usedBytes:S.isLink(i.mode)?s.size=i.link.length:s.size=0,s.atime=new Date(i.atime),s.mtime=new Date(i.mtime),s.ctime=new Date(i.ctime),s.blksize=4096,s.blocks=Math.ceil(s.size/s.blksize),s},setattr(i,s){for(const c of["mode","atime","mtime","ctime"])s[c]!=null&&(i[c]=s[c]);s.size!==void 0&&_e.resizeFileStorage(i,s.size)},lookup(i,s){throw new S.ErrnoError(44)},mknod(i,s,c,h){return _e.createNode(i,s,c,h)},rename(i,s,c){var h;try{h=S.lookupNode(s,c)}catch{}if(h){if(S.isDir(i.mode))for(var d in h.contents)throw new S.ErrnoError(55);S.hashRemoveNode(h)}delete i.parent.contents[i.name],s.contents[c]=i,i.name=c,s.ctime=s.mtime=i.parent.ctime=i.parent.mtime=Date.now()},unlink(i,s){delete i.contents[s],i.ctime=i.mtime=Date.now()},rmdir(i,s){var c=S.lookupNode(i,s);for(var h in c.contents)throw new S.ErrnoError(55);delete i.contents[s],i.ctime=i.mtime=Date.now()},readdir(i){return[".","..",...Object.keys(i.contents)]},symlink(i,s,c){var h=_e.createNode(i,s,41471,0);return h.link=c,h},readlink(i){if(!S.isLink(i.mode))throw new S.ErrnoError(28);return i.link}},stream_ops:{read(i,s,c,h,d){var g=i.node.contents;if(d>=i.node.usedBytes)return 0;var T=Math.min(i.node.usedBytes-d,h);if(D(T>=0),T>8&&g.subarray)s.set(g.subarray(d,d+T),c);else for(var b=0;b<T;b++)s[c+b]=g[d+b];return T},write(i,s,c,h,d,g){if(D(!(s instanceof ArrayBuffer)),s.buffer===Ze.buffer&&(g=!1),!h)return 0;var T=i.node;if(T.mtime=T.ctime=Date.now(),s.subarray&&(!T.contents||T.contents.subarray)){if(g)return D(d===0,"canOwn must imply no weird position inside the file"),T.contents=s.subarray(c,c+h),T.usedBytes=h,h;if(T.usedBytes===0&&d===0)return T.contents=s.slice(c,c+h),T.usedBytes=h,h;if(d+h<=T.usedBytes)return T.contents.set(s.subarray(c,c+h),d),h}if(_e.expandFileStorage(T,d+h),T.contents.subarray&&s.subarray)T.contents.set(s.subarray(c,c+h),d);else for(var b=0;b<h;b++)T.contents[d+b]=s[c+b];return T.usedBytes=Math.max(T.usedBytes,d+h),h},llseek(i,s,c){var h=s;if(c===1?h+=i.position:c===2&&S.isFile(i.node.mode)&&(h+=i.node.usedBytes),h<0)throw new S.ErrnoError(28);return h},mmap(i,s,c,h,d){if(!S.isFile(i.node.mode))throw new S.ErrnoError(43);var g,T,b=i.node.contents;if(!(d&2)&&b&&b.buffer===Ze.buffer)T=!1,g=b.byteOffset;else{if(T=!0,g=qe(),!g)throw new S.ErrnoError(48);b&&((c>0||c+s<b.length)&&(b.subarray?b=b.subarray(c,c+s):b=Array.prototype.slice.call(b,c,c+s)),Ze.set(b,g))}return{ptr:g,allocated:T}},msync(i,s,c,h,d){return _e.stream_ops.write(i,s,0,h,c,!1),0}}},ct=async i=>{var s=await E(i);return D(s,`Loading data file "${i}" failed (no arrayBuffer).`),new Uint8Array(s)},vt=(...i)=>S.createDataFile(...i),It=i=>{for(var s=i;;){if(!Pt[i])return i;i=s+Math.random()}},Mt=[],St=(i,s,c,h)=>{typeof Browser<"u"&&Browser.init();var d=!1;return Mt.forEach(g=>{d||g.canHandle(s)&&(g.handle(i,s,c,h),d=!0)}),d},Xe=(i,s,c,h,d,g,T,b,F,W)=>{var K=s?J.resolve(A.join2(i,s)):i,oe=It(`cp ${K}`);function le(ce){function fe(je){W?.(),b||vt(i,s,je,h,d,F),g?.(),w(oe)}St(ce,K,fe,()=>{T?.(),w(oe)})||fe(ce)}U(oe),typeof c=="string"?ct(c).then(le,T):le(c)},Dt=i=>{var s={r:0,"r+":2,w:577,"w+":578,a:1089,"a+":1090},c=s[i];if(typeof c>"u")throw new Error(`Unknown file open mode: ${i}`);return c},ut=(i,s)=>{var c=0;return i&&(c|=365),s&&(c|=146),c},en=i=>rt(Sc(i)),On={EPERM:63,ENOENT:44,ESRCH:71,EINTR:27,EIO:29,ENXIO:60,E2BIG:1,ENOEXEC:45,EBADF:8,ECHILD:12,EAGAIN:6,EWOULDBLOCK:6,ENOMEM:48,EACCES:2,EFAULT:21,ENOTBLK:105,EBUSY:10,EEXIST:20,EXDEV:75,ENODEV:43,ENOTDIR:54,EISDIR:31,EINVAL:28,ENFILE:41,EMFILE:33,ENOTTY:59,ETXTBSY:74,EFBIG:22,ENOSPC:51,ESPIPE:70,EROFS:69,EMLINK:34,EPIPE:64,EDOM:18,ERANGE:68,ENOMSG:49,EIDRM:24,ECHRNG:106,EL2NSYNC:156,EL3HLT:107,EL3RST:108,ELNRNG:109,EUNATCH:110,ENOCSI:111,EL2HLT:112,EDEADLK:16,ENOLCK:46,EBADE:113,EBADR:114,EXFULL:115,ENOANO:104,EBADRQC:103,EBADSLT:102,EDEADLOCK:16,EBFONT:101,ENOSTR:100,ENODATA:116,ETIME:117,ENOSR:118,ENONET:119,ENOPKG:120,EREMOTE:121,ENOLINK:47,EADV:122,ESRMNT:123,ECOMM:124,EPROTO:65,EMULTIHOP:36,EDOTDOT:125,EBADMSG:9,ENOTUNIQ:126,EBADFD:127,EREMCHG:128,ELIBACC:129,ELIBBAD:130,ELIBSCN:131,ELIBMAX:132,ELIBEXEC:133,ENOSYS:52,ENOTEMPTY:55,ENAMETOOLONG:37,ELOOP:32,EOPNOTSUPP:138,EPFNOSUPPORT:139,ECONNRESET:15,ENOBUFS:42,EAFNOSUPPORT:5,EPROTOTYPE:67,ENOTSOCK:57,ENOPROTOOPT:50,ESHUTDOWN:140,ECONNREFUSED:14,EADDRINUSE:3,ECONNABORTED:13,ENETUNREACH:40,ENETDOWN:38,ETIMEDOUT:73,EHOSTDOWN:142,EHOSTUNREACH:23,EINPROGRESS:26,EALREADY:7,EDESTADDRREQ:17,EMSGSIZE:35,EPROTONOSUPPORT:66,ESOCKTNOSUPPORT:137,EADDRNOTAVAIL:4,ENETRESET:39,EISCONN:30,ENOTCONN:53,ETOOMANYREFS:141,EUSERS:136,EDQUOT:19,ESTALE:72,ENOTSUP:138,ENOMEDIUM:148,EILSEQ:25,EOVERFLOW:61,ECANCELED:11,ENOTRECOVERABLE:56,EOWNERDEAD:62,ESTRPIPE:135},S={root:null,mounts:[],devices:{},streams:[],nextInode:1,nameTable:null,currentPath:"/",initialized:!1,ignorePermissions:!0,filesystems:null,syncFSRequests:0,readFiles:{},ErrnoError:class extends Error{name="ErrnoError";constructor(i){super(_t?en(i):""),this.errno=i;for(var s in On)if(On[s]===i){this.code=s;break}}},FSStream:class{shared={};get object(){return this.node}set object(i){this.node=i}get isRead(){return(this.flags&2097155)!==1}get isWrite(){return(this.flags&2097155)!==0}get isAppend(){return this.flags&1024}get flags(){return this.shared.flags}set flags(i){this.shared.flags=i}get position(){return this.shared.position}set position(i){this.shared.position=i}},FSNode:class{node_ops={};stream_ops={};readMode=365;writeMode=146;mounted=null;constructor(i,s,c,h){i||(i=this),this.parent=i,this.mount=i.mount,this.id=S.nextInode++,this.name=s,this.mode=c,this.rdev=h,this.atime=this.mtime=this.ctime=Date.now()}get read(){return(this.mode&this.readMode)===this.readMode}set read(i){i?this.mode|=this.readMode:this.mode&=~this.readMode}get write(){return(this.mode&this.writeMode)===this.writeMode}set write(i){i?this.mode|=this.writeMode:this.mode&=~this.writeMode}get isFolder(){return S.isDir(this.mode)}get isDevice(){return S.isChrdev(this.mode)}},lookupPath(i,s={}){if(!i)throw new S.ErrnoError(44);s.follow_mount??=!0,A.isAbs(i)||(i=S.cwd()+"/"+i);e:for(var c=0;c<40;c++){for(var h=i.split("/").filter(W=>!!W),d=S.root,g="/",T=0;T<h.length;T++){var b=T===h.length-1;if(b&&s.parent)break;if(h[T]!=="."){if(h[T]===".."){if(g=A.dirname(g),S.isRoot(d)){i=g+"/"+h.slice(T+1).join("/");continue e}else d=d.parent;continue}g=A.join2(g,h[T]);try{d=S.lookupNode(d,h[T])}catch(W){if(W?.errno===44&&b&&s.noent_okay)return{path:g};throw W}if(S.isMountpoint(d)&&(!b||s.follow_mount)&&(d=d.mounted.root),S.isLink(d.mode)&&(!b||s.follow)){if(!d.node_ops.readlink)throw new S.ErrnoError(52);var F=d.node_ops.readlink(d);A.isAbs(F)||(F=A.dirname(g)+"/"+F),i=F+"/"+h.slice(T+1).join("/");continue e}}}return{path:g,node:d}}throw new S.ErrnoError(32)},getPath(i){for(var s;;){if(S.isRoot(i)){var c=i.mount.mountpoint;return s?c[c.length-1]!=="/"?`${c}/${s}`:c+s:c}s=s?`${i.name}/${s}`:i.name,i=i.parent}},hashName(i,s){for(var c=0,h=0;h<s.length;h++)c=(c<<5)-c+s.charCodeAt(h)|0;return(i+c>>>0)%S.nameTable.length},hashAddNode(i){var s=S.hashName(i.parent.id,i.name);i.name_next=S.nameTable[s],S.nameTable[s]=i},hashRemoveNode(i){var s=S.hashName(i.parent.id,i.name);if(S.nameTable[s]===i)S.nameTable[s]=i.name_next;else for(var c=S.nameTable[s];c;){if(c.name_next===i){c.name_next=i.name_next;break}c=c.name_next}},lookupNode(i,s){var c=S.mayLookup(i);if(c)throw new S.ErrnoError(c);for(var h=S.hashName(i.id,s),d=S.nameTable[h];d;d=d.name_next){var g=d.name;if(d.parent.id===i.id&&g===s)return d}return S.lookup(i,s)},createNode(i,s,c,h){D(typeof i=="object");var d=new S.FSNode(i,s,c,h);return S.hashAddNode(d),d},destroyNode(i){S.hashRemoveNode(i)},isRoot(i){return i===i.parent},isMountpoint(i){return!!i.mounted},isFile(i){return(i&61440)===32768},isDir(i){return(i&61440)===16384},isLink(i){return(i&61440)===40960},isChrdev(i){return(i&61440)===8192},isBlkdev(i){return(i&61440)===24576},isFIFO(i){return(i&61440)===4096},isSocket(i){return(i&49152)===49152},flagsToPermissionString(i){var s=["r","w","rw"][i&3];return i&512&&(s+="w"),s},nodePermissions(i,s){return S.ignorePermissions?0:s.includes("r")&&!(i.mode&292)||s.includes("w")&&!(i.mode&146)||s.includes("x")&&!(i.mode&73)?2:0},mayLookup(i){if(!S.isDir(i.mode))return 54;var s=S.nodePermissions(i,"x");return s||(i.node_ops.lookup?0:2)},mayCreate(i,s){if(!S.isDir(i.mode))return 54;try{var c=S.lookupNode(i,s);return 20}catch{}return S.nodePermissions(i,"wx")},mayDelete(i,s,c){var h;try{h=S.lookupNode(i,s)}catch(g){return g.errno}var d=S.nodePermissions(i,"wx");if(d)return d;if(c){if(!S.isDir(h.mode))return 54;if(S.isRoot(h)||S.getPath(h)===S.cwd())return 10}else if(S.isDir(h.mode))return 31;return 0},mayOpen(i,s){return i?S.isLink(i.mode)?32:S.isDir(i.mode)&&(S.flagsToPermissionString(s)!=="r"||s&576)?31:S.nodePermissions(i,S.flagsToPermissionString(s)):44},checkOpExists(i,s){if(!i)throw new S.ErrnoError(s);return i},MAX_OPEN_FDS:4096,nextfd(){for(var i=0;i<=S.MAX_OPEN_FDS;i++)if(!S.streams[i])return i;throw new S.ErrnoError(33)},getStreamChecked(i){var s=S.getStream(i);if(!s)throw new S.ErrnoError(8);return s},getStream:i=>S.streams[i],createStream(i,s=-1){return D(s>=-1),i=Object.assign(new S.FSStream,i),s==-1&&(s=S.nextfd()),i.fd=s,S.streams[s]=i,i},closeStream(i){S.streams[i]=null},dupStream(i,s=-1){var c=S.createStream(i,s);return c.stream_ops?.dup?.(c),c},doSetAttr(i,s,c){var h=i?.stream_ops.setattr,d=h?i:s;h??=s.node_ops.setattr,S.checkOpExists(h,63),h(d,c)},chrdev_stream_ops:{open(i){var s=S.getDevice(i.node.rdev);i.stream_ops=s.stream_ops,i.stream_ops.open?.(i)},llseek(){throw new S.ErrnoError(70)}},major:i=>i>>8,minor:i=>i&255,makedev:(i,s)=>i<<8|s,registerDevice(i,s){S.devices[i]={stream_ops:s}},getDevice:i=>S.devices[i],getMounts(i){for(var s=[],c=[i];c.length;){var h=c.pop();s.push(h),c.push(...h.mounts)}return s},syncfs(i,s){typeof i=="function"&&(s=i,i=!1),S.syncFSRequests++,S.syncFSRequests>1&&I(`warning: ${S.syncFSRequests} FS.syncfs operations in flight at once, probably just doing extra work`);var c=S.getMounts(S.root.mount),h=0;function d(T){return D(S.syncFSRequests>0),S.syncFSRequests--,s(T)}function g(T){if(T)return g.errored?void 0:(g.errored=!0,d(T));++h>=c.length&&d(null)}c.forEach(T=>{if(!T.type.syncfs)return g(null);T.type.syncfs(T,i,g)})},mount(i,s,c){if(typeof i=="string")throw i;var h=c==="/",d=!c,g;if(h&&S.root)throw new S.ErrnoError(10);if(!h&&!d){var T=S.lookupPath(c,{follow_mount:!1});if(c=T.path,g=T.node,S.isMountpoint(g))throw new S.ErrnoError(10);if(!S.isDir(g.mode))throw new S.ErrnoError(54)}var b={type:i,opts:s,mountpoint:c,mounts:[]},F=i.mount(b);return F.mount=b,b.root=F,h?S.root=F:g&&(g.mounted=b,g.mount&&g.mount.mounts.push(b)),F},unmount(i){var s=S.lookupPath(i,{follow_mount:!1});if(!S.isMountpoint(s.node))throw new S.ErrnoError(28);var c=s.node,h=c.mounted,d=S.getMounts(h);Object.keys(S.nameTable).forEach(T=>{for(var b=S.nameTable[T];b;){var F=b.name_next;d.includes(b.mount)&&S.destroyNode(b),b=F}}),c.mounted=null;var g=c.mount.mounts.indexOf(h);D(g!==-1),c.mount.mounts.splice(g,1)},lookup(i,s){return i.node_ops.lookup(i,s)},mknod(i,s,c){var h=S.lookupPath(i,{parent:!0}),d=h.node,g=A.basename(i);if(!g)throw new S.ErrnoError(28);if(g==="."||g==="..")throw new S.ErrnoError(20);var T=S.mayCreate(d,g);if(T)throw new S.ErrnoError(T);if(!d.node_ops.mknod)throw new S.ErrnoError(63);return d.node_ops.mknod(d,g,s,c)},statfs(i){return S.statfsNode(S.lookupPath(i,{follow:!0}).node)},statfsStream(i){return S.statfsNode(i.node)},statfsNode(i){var s={bsize:4096,frsize:4096,blocks:1e6,bfree:5e5,bavail:5e5,files:S.nextInode,ffree:S.nextInode-1,fsid:42,flags:2,namelen:255};return i.node_ops.statfs&&Object.assign(s,i.node_ops.statfs(i.mount.opts.root)),s},create(i,s=438){return s&=4095,s|=32768,S.mknod(i,s,0)},mkdir(i,s=511){return s&=1023,s|=16384,S.mknod(i,s,0)},mkdirTree(i,s){var c=i.split("/"),h="";for(var d of c)if(d){(h||A.isAbs(i))&&(h+="/"),h+=d;try{S.mkdir(h,s)}catch(g){if(g.errno!=20)throw g}}},mkdev(i,s,c){return typeof c>"u"&&(c=s,s=438),s|=8192,S.mknod(i,s,c)},symlink(i,s){if(!J.resolve(i))throw new S.ErrnoError(44);var c=S.lookupPath(s,{parent:!0}),h=c.node;if(!h)throw new S.ErrnoError(44);var d=A.basename(s),g=S.mayCreate(h,d);if(g)throw new S.ErrnoError(g);if(!h.node_ops.symlink)throw new S.ErrnoError(63);return h.node_ops.symlink(h,d,i)},rename(i,s){var c=A.dirname(i),h=A.dirname(s),d=A.basename(i),g=A.basename(s),T,b,F;if(T=S.lookupPath(i,{parent:!0}),b=T.node,T=S.lookupPath(s,{parent:!0}),F=T.node,!b||!F)throw new S.ErrnoError(44);if(b.mount!==F.mount)throw new S.ErrnoError(75);var W=S.lookupNode(b,d),K=J.relative(i,h);if(K.charAt(0)!==".")throw new S.ErrnoError(28);if(K=J.relative(s,c),K.charAt(0)!==".")throw new S.ErrnoError(55);var oe;try{oe=S.lookupNode(F,g)}catch{}if(W!==oe){var le=S.isDir(W.mode),ce=S.mayDelete(b,d,le);if(ce)throw new S.ErrnoError(ce);if(ce=oe?S.mayDelete(F,g,le):S.mayCreate(F,g),ce)throw new S.ErrnoError(ce);if(!b.node_ops.rename)throw new S.ErrnoError(63);if(S.isMountpoint(W)||oe&&S.isMountpoint(oe))throw new S.ErrnoError(10);if(F!==b&&(ce=S.nodePermissions(b,"w"),ce))throw new S.ErrnoError(ce);S.hashRemoveNode(W);try{b.node_ops.rename(W,F,g),W.parent=F}catch(fe){throw fe}finally{S.hashAddNode(W)}}},rmdir(i){var s=S.lookupPath(i,{parent:!0}),c=s.node,h=A.basename(i),d=S.lookupNode(c,h),g=S.mayDelete(c,h,!0);if(g)throw new S.ErrnoError(g);if(!c.node_ops.rmdir)throw new S.ErrnoError(63);if(S.isMountpoint(d))throw new S.ErrnoError(10);c.node_ops.rmdir(c,h),S.destroyNode(d)},readdir(i){var s=S.lookupPath(i,{follow:!0}),c=s.node,h=S.checkOpExists(c.node_ops.readdir,54);return h(c)},unlink(i){var s=S.lookupPath(i,{parent:!0}),c=s.node;if(!c)throw new S.ErrnoError(44);var h=A.basename(i),d=S.lookupNode(c,h),g=S.mayDelete(c,h,!1);if(g)throw new S.ErrnoError(g);if(!c.node_ops.unlink)throw new S.ErrnoError(63);if(S.isMountpoint(d))throw new S.ErrnoError(10);c.node_ops.unlink(c,h),S.destroyNode(d)},readlink(i){var s=S.lookupPath(i),c=s.node;if(!c)throw new S.ErrnoError(44);if(!c.node_ops.readlink)throw new S.ErrnoError(28);return c.node_ops.readlink(c)},stat(i,s){var c=S.lookupPath(i,{follow:!s}),h=c.node,d=S.checkOpExists(h.node_ops.getattr,63);return d(h)},fstat(i){var s=S.getStreamChecked(i),c=s.node,h=s.stream_ops.getattr,d=h?s:c;return h??=c.node_ops.getattr,S.checkOpExists(h,63),h(d)},lstat(i){return S.stat(i,!0)},doChmod(i,s,c,h){S.doSetAttr(i,s,{mode:c&4095|s.mode&-4096,ctime:Date.now(),dontFollow:h})},chmod(i,s,c){var h;if(typeof i=="string"){var d=S.lookupPath(i,{follow:!c});h=d.node}else h=i;S.doChmod(null,h,s,c)},lchmod(i,s){S.chmod(i,s,!0)},fchmod(i,s){var c=S.getStreamChecked(i);S.doChmod(c,c.node,s,!1)},doChown(i,s,c){S.doSetAttr(i,s,{timestamp:Date.now(),dontFollow:c})},chown(i,s,c,h){var d;if(typeof i=="string"){var g=S.lookupPath(i,{follow:!h});d=g.node}else d=i;S.doChown(null,d,h)},lchown(i,s,c){S.chown(i,s,c,!0)},fchown(i,s,c){var h=S.getStreamChecked(i);S.doChown(h,h.node,!1)},doTruncate(i,s,c){if(S.isDir(s.mode))throw new S.ErrnoError(31);if(!S.isFile(s.mode))throw new S.ErrnoError(28);var h=S.nodePermissions(s,"w");if(h)throw new S.ErrnoError(h);S.doSetAttr(i,s,{size:c,timestamp:Date.now()})},truncate(i,s){if(s<0)throw new S.ErrnoError(28);var c;if(typeof i=="string"){var h=S.lookupPath(i,{follow:!0});c=h.node}else c=i;S.doTruncate(null,c,s)},ftruncate(i,s){var c=S.getStreamChecked(i);if(s<0||(c.flags&2097155)===0)throw new S.ErrnoError(28);S.doTruncate(c,c.node,s)},utime(i,s,c){var h=S.lookupPath(i,{follow:!0}),d=h.node,g=S.checkOpExists(d.node_ops.setattr,63);g(d,{atime:s,mtime:c})},open(i,s,c=438){if(i==="")throw new S.ErrnoError(44);s=typeof s=="string"?Dt(s):s,s&64?c=c&4095|32768:c=0;var h,d;if(typeof i=="object")h=i;else{d=i.endsWith("/");var g=S.lookupPath(i,{follow:!(s&131072),noent_okay:!0});h=g.node,i=g.path}var T=!1;if(s&64)if(h){if(s&128)throw new S.ErrnoError(20)}else{if(d)throw new S.ErrnoError(31);h=S.mknod(i,c|511,0),T=!0}if(!h)throw new S.ErrnoError(44);if(S.isChrdev(h.mode)&&(s&=-513),s&65536&&!S.isDir(h.mode))throw new S.ErrnoError(54);if(!T){var b=S.mayOpen(h,s);if(b)throw new S.ErrnoError(b)}s&512&&!T&&S.truncate(h,0),s&=-131713;var F=S.createStream({node:h,path:S.getPath(h),flags:s,seekable:!0,position:0,stream_ops:h.stream_ops,ungotten:[],error:!1});return F.stream_ops.open&&F.stream_ops.open(F),T&&S.chmod(h,c&511),t.logReadFiles&&!(s&1)&&(i in S.readFiles||(S.readFiles[i]=1)),F},close(i){if(S.isClosed(i))throw new S.ErrnoError(8);i.getdents&&(i.getdents=null);try{i.stream_ops.close&&i.stream_ops.close(i)}catch(s){throw s}finally{S.closeStream(i.fd)}i.fd=null},isClosed(i){return i.fd===null},llseek(i,s,c){if(S.isClosed(i))throw new S.ErrnoError(8);if(!i.seekable||!i.stream_ops.llseek)throw new S.ErrnoError(70);if(c!=0&&c!=1&&c!=2)throw new S.ErrnoError(28);return i.position=i.stream_ops.llseek(i,s,c),i.ungotten=[],i.position},read(i,s,c,h,d){if(D(c>=0),h<0||d<0)throw new S.ErrnoError(28);if(S.isClosed(i))throw new S.ErrnoError(8);if((i.flags&2097155)===1)throw new S.ErrnoError(8);if(S.isDir(i.node.mode))throw new S.ErrnoError(31);if(!i.stream_ops.read)throw new S.ErrnoError(28);var g=typeof d<"u";if(!g)d=i.position;else if(!i.seekable)throw new S.ErrnoError(70);var T=i.stream_ops.read(i,s,c,h,d);return g||(i.position+=T),T},write(i,s,c,h,d,g){if(D(c>=0),h<0||d<0)throw new S.ErrnoError(28);if(S.isClosed(i))throw new S.ErrnoError(8);if((i.flags&2097155)===0)throw new S.ErrnoError(8);if(S.isDir(i.node.mode))throw new S.ErrnoError(31);if(!i.stream_ops.write)throw new S.ErrnoError(28);i.seekable&&i.flags&1024&&S.llseek(i,0,2);var T=typeof d<"u";if(!T)d=i.position;else if(!i.seekable)throw new S.ErrnoError(70);var b=i.stream_ops.write(i,s,c,h,d,g);return T||(i.position+=b),b},mmap(i,s,c,h,d){if((h&2)!==0&&(d&2)===0&&(i.flags&2097155)!==2)throw new S.ErrnoError(2);if((i.flags&2097155)===1)throw new S.ErrnoError(2);if(!i.stream_ops.mmap)throw new S.ErrnoError(43);if(!s)throw new S.ErrnoError(28);return i.stream_ops.mmap(i,s,c,h,d)},msync(i,s,c,h,d){return D(c>=0),i.stream_ops.msync?i.stream_ops.msync(i,s,c,h,d):0},ioctl(i,s,c){if(!i.stream_ops.ioctl)throw new S.ErrnoError(59);return i.stream_ops.ioctl(i,s,c)},readFile(i,s={}){if(s.flags=s.flags||0,s.encoding=s.encoding||"binary",s.encoding!=="utf8"&&s.encoding!=="binary")throw new Error(`Invalid encoding type "${s.encoding}"`);var c=S.open(i,s.flags),h=S.stat(i),d=h.size,g=new Uint8Array(d);return S.read(c,g,0,d,0),s.encoding==="utf8"&&(g=pt(g)),S.close(c),g},writeFile(i,s,c={}){c.flags=c.flags||577;var h=S.open(i,c.flags,c.mode);if(typeof s=="string"&&(s=new Uint8Array(Ne(s))),ArrayBuffer.isView(s))S.write(h,s,0,s.byteLength,void 0,c.canOwn);else throw new Error("Unsupported data type");S.close(h)},cwd:()=>S.currentPath,chdir(i){var s=S.lookupPath(i,{follow:!0});if(s.node===null)throw new S.ErrnoError(44);if(!S.isDir(s.node.mode))throw new S.ErrnoError(54);var c=S.nodePermissions(s.node,"x");if(c)throw new S.ErrnoError(c);S.currentPath=s.path},createDefaultDirectories(){S.mkdir("/tmp"),S.mkdir("/home"),S.mkdir("/home/web_user")},createDefaultDevices(){S.mkdir("/dev"),S.registerDevice(S.makedev(1,3),{read:()=>0,write:(h,d,g,T,b)=>T,llseek:()=>0}),S.mkdev("/dev/null",S.makedev(1,3)),He.register(S.makedev(5,0),He.default_tty_ops),He.register(S.makedev(6,0),He.default_tty1_ops),S.mkdev("/dev/tty",S.makedev(5,0)),S.mkdev("/dev/tty1",S.makedev(6,0));var i=new Uint8Array(1024),s=0,c=()=>(s===0&&(Q(i),s=i.byteLength),i[--s]);S.createDevice("/dev","random",c),S.createDevice("/dev","urandom",c),S.mkdir("/dev/shm"),S.mkdir("/dev/shm/tmp")},createSpecialDirectories(){S.mkdir("/proc");var i=S.mkdir("/proc/self");S.mkdir("/proc/self/fd"),S.mount({mount(){var s=S.createNode(i,"fd",16895,73);return s.stream_ops={llseek:_e.stream_ops.llseek},s.node_ops={lookup(c,h){var d=+h,g=S.getStreamChecked(d),T={parent:null,mount:{mountpoint:"fake"},node_ops:{readlink:()=>g.path},id:d+1};return T.parent=T,T},readdir(){return Array.from(S.streams.entries()).filter(([c,h])=>h).map(([c,h])=>c.toString())}},s}},{},"/proc/self/fd")},createStandardStreams(i,s,c){i?S.createDevice("/dev","stdin",i):S.symlink("/dev/tty","/dev/stdin"),s?S.createDevice("/dev","stdout",null,s):S.symlink("/dev/tty","/dev/stdout"),c?S.createDevice("/dev","stderr",null,c):S.symlink("/dev/tty1","/dev/stderr");var h=S.open("/dev/stdin",0),d=S.open("/dev/stdout",1),g=S.open("/dev/stderr",1);D(h.fd===0,`invalid handle for stdin (${h.fd})`),D(d.fd===1,`invalid handle for stdout (${d.fd})`),D(g.fd===2,`invalid handle for stderr (${g.fd})`)},staticInit(){S.nameTable=new Array(4096),S.mount(_e,{},"/"),S.createDefaultDirectories(),S.createDefaultDevices(),S.createSpecialDirectories(),S.filesystems={MEMFS:_e}},init(i,s,c){D(!S.initialized,"FS.init was previously called. If you want to initialize later with custom parameters, remove any earlier calls (note that one is automatically added to the generated code)"),S.initialized=!0,i??=t.stdin,s??=t.stdout,c??=t.stderr,S.createStandardStreams(i,s,c)},quit(){S.initialized=!1,ea(0);for(var i of S.streams)i&&S.close(i)},findObject(i,s){var c=S.analyzePath(i,s);return c.exists?c.object:null},analyzePath(i,s){try{var c=S.lookupPath(i,{follow:!s});i=c.path}catch{}var h={isRoot:!1,exists:!1,error:0,name:null,path:null,object:null,parentExists:!1,parentPath:null,parentObject:null};try{var c=S.lookupPath(i,{parent:!0});h.parentExists=!0,h.parentPath=c.path,h.parentObject=c.node,h.name=A.basename(i),c=S.lookupPath(i,{follow:!s}),h.exists=!0,h.path=c.path,h.object=c.node,h.name=c.node.name,h.isRoot=c.path==="/"}catch(d){h.error=d.errno}return h},createPath(i,s,c,h){i=typeof i=="string"?i:S.getPath(i);for(var d=s.split("/").reverse();d.length;){var g=d.pop();if(g){var T=A.join2(i,g);try{S.mkdir(T)}catch(b){if(b.errno!=20)throw b}i=T}}return T},createFile(i,s,c,h,d){var g=A.join2(typeof i=="string"?i:S.getPath(i),s),T=ut(h,d);return S.create(g,T)},createDataFile(i,s,c,h,d,g){var T=s;i&&(i=typeof i=="string"?i:S.getPath(i),T=s?A.join2(i,s):i);var b=ut(h,d),F=S.create(T,b);if(c){if(typeof c=="string"){for(var W=new Array(c.length),K=0,oe=c.length;K<oe;++K)W[K]=c.charCodeAt(K);c=W}S.chmod(F,b|146);var le=S.open(F,577);S.write(le,c,0,c.length,0,g),S.close(le),S.chmod(F,b)}},createDevice(i,s,c,h){var d=A.join2(typeof i=="string"?i:S.getPath(i),s),g=ut(!!c,!!h);S.createDevice.major??=64;var T=S.makedev(S.createDevice.major++,0);return S.registerDevice(T,{open(b){b.seekable=!1},close(b){h?.buffer?.length&&h(10)},read(b,F,W,K,oe){for(var le=0,ce=0;ce<K;ce++){var fe;try{fe=c()}catch{throw new S.ErrnoError(29)}if(fe===void 0&&le===0)throw new S.ErrnoError(6);if(fe==null)break;le++,F[W+ce]=fe}return le&&(b.node.atime=Date.now()),le},write(b,F,W,K,oe){for(var le=0;le<K;le++)try{h(F[W+le])}catch{throw new S.ErrnoError(29)}return K&&(b.node.mtime=b.node.ctime=Date.now()),le}}),S.mkdev(d,g,T)},forceLoadFile(i){if(i.isDevice||i.isFolder||i.link||i.contents)return!0;if(typeof XMLHttpRequest<"u")throw new Error("Lazy loading should have been performed (contents set) in createLazyFile, but it was not. Lazy loading only works in web workers. Use --embed-file or --preload-file in emcc on the main thread.");try{i.contents=R(i.url),i.usedBytes=i.contents.length}catch{throw new S.ErrnoError(29)}},createLazyFile(i,s,c,h,d){class g{lengthKnown=!1;chunks=[];get(ce){if(!(ce>this.length-1||ce<0)){var fe=ce%this.chunkSize,je=ce/this.chunkSize|0;return this.getter(je)[fe]}}setDataGetter(ce){this.getter=ce}cacheLength(){var ce=new XMLHttpRequest;if(ce.open("HEAD",c,!1),ce.send(null),!(ce.status>=200&&ce.status<300||ce.status===304))throw new Error("Couldn't load "+c+". Status: "+ce.status);var fe=Number(ce.getResponseHeader("Content-length")),je,ht=(je=ce.getResponseHeader("Accept-Ranges"))&&je==="bytes",st=(je=ce.getResponseHeader("Content-Encoding"))&&je==="gzip",Rt=1024*1024;ht||(Rt=fe);var mt=(Vt,tn)=>{if(Vt>tn)throw new Error("invalid range ("+Vt+", "+tn+") or no bytes requested!");if(tn>fe-1)throw new Error("only "+fe+" bytes available! programmer error!");var Tt=new XMLHttpRequest;if(Tt.open("GET",c,!1),fe!==Rt&&Tt.setRequestHeader("Range","bytes="+Vt+"-"+tn),Tt.responseType="arraybuffer",Tt.overrideMimeType&&Tt.overrideMimeType("text/plain; charset=x-user-defined"),Tt.send(null),!(Tt.status>=200&&Tt.status<300||Tt.status===304))throw new Error("Couldn't load "+c+". Status: "+Tt.status);return Tt.response!==void 0?new Uint8Array(Tt.response||[]):Ne(Tt.responseText||"")},Zt=this;Zt.setDataGetter(Vt=>{var tn=Vt*Rt,Tt=(Vt+1)*Rt-1;if(Tt=Math.min(Tt,fe-1),typeof Zt.chunks[Vt]>"u"&&(Zt.chunks[Vt]=mt(tn,Tt)),typeof Zt.chunks[Vt]>"u")throw new Error("doXHR failed!");return Zt.chunks[Vt]}),(st||!fe)&&(Rt=fe=1,fe=this.getter(0).length,Rt=fe,N("LazyFiles on gzip forces download of the whole file when length is accessed")),this._length=fe,this._chunkSize=Rt,this.lengthKnown=!0}get length(){return this.lengthKnown||this.cacheLength(),this._length}get chunkSize(){return this.lengthKnown||this.cacheLength(),this._chunkSize}}if(typeof XMLHttpRequest<"u"){if(!a)throw"Cannot do synchronous binary XHRs outside webworkers in modern browsers. Use --embed-file or --preload-file in emcc";var T=new g,b={isDevice:!1,contents:T}}else var b={isDevice:!1,url:c};var F=S.createFile(i,s,b,h,d);b.contents?F.contents=b.contents:b.url&&(F.contents=null,F.url=b.url),Object.defineProperties(F,{usedBytes:{get:function(){return this.contents.length}}});var W={},K=Object.keys(F.stream_ops);K.forEach(le=>{var ce=F.stream_ops[le];W[le]=(...fe)=>(S.forceLoadFile(F),ce(...fe))});function oe(le,ce,fe,je,ht){var st=le.node.contents;if(ht>=st.length)return 0;var Rt=Math.min(st.length-ht,je);if(D(Rt>=0),st.slice)for(var mt=0;mt<Rt;mt++)ce[fe+mt]=st[ht+mt];else for(var mt=0;mt<Rt;mt++)ce[fe+mt]=st.get(ht+mt);return Rt}return W.read=(le,ce,fe,je,ht)=>(S.forceLoadFile(F),oe(le,ce,fe,je,ht)),W.mmap=(le,ce,fe,je,ht)=>{S.forceLoadFile(F);var st=qe();if(!st)throw new S.ErrnoError(48);return oe(le,Ze,st,ce,fe),{ptr:st,allocated:!0}},F.stream_ops=W,F},absolutePath(){Y("FS.absolutePath has been removed; use PATH_FS.resolve instead")},createFolder(){Y("FS.createFolder has been removed; use FS.mkdir instead")},createLink(){Y("FS.createLink has been removed; use FS.symlink instead")},joinPath(){Y("FS.joinPath has been removed; use PATH.join instead")},mmapAlloc(){Y("FS.mmapAlloc has been replaced by the top level function mmapAlloc")},standardizePath(){Y("FS.standardizePath has been removed; use PATH.normalize instead")}},yt={DEFAULT_POLLMASK:5,calculateAt(i,s,c){if(A.isAbs(s))return s;var h;if(i===-100)h=S.cwd();else{var d=yt.getStreamFromFD(i);h=d.path}if(s.length==0){if(!c)throw new S.ErrnoError(44);return h}return h+"/"+s},writeStat(i,s){ue[i>>2]=s.dev,ue[i+4>>2]=s.mode,ve[i+8>>2]=s.nlink,ue[i+12>>2]=s.uid,ue[i+16>>2]=s.gid,ue[i+20>>2]=s.rdev,Qe[i+24>>3]=BigInt(s.size),ue[i+32>>2]=4096,ue[i+36>>2]=s.blocks;var c=s.atime.getTime(),h=s.mtime.getTime(),d=s.ctime.getTime();return Qe[i+40>>3]=BigInt(Math.floor(c/1e3)),ve[i+48>>2]=c%1e3*1e3*1e3,Qe[i+56>>3]=BigInt(Math.floor(h/1e3)),ve[i+64>>2]=h%1e3*1e3*1e3,Qe[i+72>>3]=BigInt(Math.floor(d/1e3)),ve[i+80>>2]=d%1e3*1e3*1e3,Qe[i+88>>3]=BigInt(s.ino),0},writeStatFs(i,s){ue[i+4>>2]=s.bsize,ue[i+40>>2]=s.bsize,ue[i+8>>2]=s.blocks,ue[i+12>>2]=s.bfree,ue[i+16>>2]=s.bavail,ue[i+20>>2]=s.files,ue[i+24>>2]=s.ffree,ue[i+28>>2]=s.fsid,ue[i+44>>2]=s.flags,ue[i+36>>2]=s.namelen},doMsync(i,s,c,h,d){if(!S.isFile(s.node.mode))throw new S.ErrnoError(43);if(h&2)return 0;var g=ie.slice(i,i+c);S.msync(s,g,d,c,h)},getStreamFromFD(i){var s=S.getStreamChecked(i);return s},varargs:void 0,getStr(i){var s=rt(i);return s}};function Lt(i,s,c){try{var h=yt.getStreamFromFD(i);if(D(!c),h.fd===s)return-28;if(s<0||s>=S.MAX_OPEN_FDS)return-8;var d=S.getStream(s);return d&&S.close(d),S.dupStream(h,s).fd}catch(g){if(typeof S>"u"||g.name!=="ErrnoError")throw g;return-g.errno}}var qt=()=>{D(yt.varargs!=null);var i=ue[+yt.varargs>>2];return yt.varargs+=4,i},Bt=qt;function Yt(i,s,c){yt.varargs=c;try{var h=yt.getStreamFromFD(i);switch(s){case 0:{var d=qt();if(d<0)return-28;for(;S.streams[d];)d++;var g;return g=S.dupStream(h,d),g.fd}case 1:case 2:return 0;case 3:return h.flags;case 4:{var d=qt();return h.flags|=d,0}case 12:{var d=Bt(),T=0;return Te[d+T>>1]=2,0}case 13:case 14:return 0}return-28}catch(b){if(typeof S>"u"||b.name!=="ErrnoError")throw b;return-b.errno}}function Kt(i,s){try{return yt.writeStat(s,S.fstat(i))}catch(c){if(typeof S>"u"||c.name!=="ErrnoError")throw c;return-c.errno}}function lr(i,s,c){yt.varargs=c;try{var h=yt.getStreamFromFD(i);switch(s){case 21509:return h.tty?0:-59;case 21505:{if(!h.tty)return-59;if(h.tty.ops.ioctl_tcgets){var d=h.tty.ops.ioctl_tcgets(h),g=Bt();ue[g>>2]=d.c_iflag||0,ue[g+4>>2]=d.c_oflag||0,ue[g+8>>2]=d.c_cflag||0,ue[g+12>>2]=d.c_lflag||0;for(var T=0;T<32;T++)Ze[g+T+17]=d.c_cc[T]||0;return 0}return 0}case 21510:case 21511:case 21512:return h.tty?0:-59;case 21506:case 21507:case 21508:{if(!h.tty)return-59;if(h.tty.ops.ioctl_tcsets){for(var g=Bt(),b=ue[g>>2],F=ue[g+4>>2],W=ue[g+8>>2],K=ue[g+12>>2],oe=[],T=0;T<32;T++)oe.push(Ze[g+T+17]);return h.tty.ops.ioctl_tcsets(h.tty,s,{c_iflag:b,c_oflag:F,c_cflag:W,c_lflag:K,c_cc:oe})}return 0}case 21519:{if(!h.tty)return-59;var g=Bt();return ue[g>>2]=0,0}case 21520:return h.tty?-28:-59;case 21531:{var g=Bt();return S.ioctl(h,s,g)}case 21523:{if(!h.tty)return-59;if(h.tty.ops.ioctl_tiocgwinsz){var le=h.tty.ops.ioctl_tiocgwinsz(h.tty),g=Bt();Te[g>>1]=le[0],Te[g+2>>1]=le[1]}return 0}case 21524:return h.tty?0:-59;case 21515:return h.tty?0:-59;default:return-28}}catch(ce){if(typeof S>"u"||ce.name!=="ErrnoError")throw ce;return-ce.errno}}function kn(i,s){try{return i=yt.getStr(i),yt.writeStat(s,S.lstat(i))}catch(c){if(typeof S>"u"||c.name!=="ErrnoError")throw c;return-c.errno}}function Pu(i,s,c,h){try{s=yt.getStr(s);var d=h&256,g=h&4096;return h=h&-6401,D(!h,`unknown flags in __syscall_newfstatat: ${h}`),s=yt.calculateAt(i,s,g),yt.writeStat(c,d?S.lstat(s):S.stat(s))}catch(T){if(typeof S>"u"||T.name!=="ErrnoError")throw T;return-T.errno}}function Du(i,s,c,h){yt.varargs=h;try{s=yt.getStr(s),s=yt.calculateAt(i,s);var d=h?qt():0;return S.open(s,c,d).fd}catch(g){if(typeof S>"u"||g.name!=="ErrnoError")throw g;return-g.errno}}function Lu(i,s){try{return i=yt.getStr(i),yt.writeStat(s,S.stat(i))}catch(c){if(typeof S>"u"||c.name!=="ErrnoError")throw c;return-c.errno}}var Iu=()=>Y("native code called abort()"),zt=i=>{for(var s="";;){var c=ie[i++];if(!c)return s;s+=String.fromCharCode(c)}},Ii={},hi={},Fr={},ur=class extends Error{constructor(s){super(s),this.name="BindingError"}},dt=i=>{throw new ur(i)};function Fu(i,s,c={}){var h=s.name;if(i||dt(`type "${h}" must have a positive integer typeid pointer`),hi.hasOwnProperty(i)){if(c.ignoreDuplicateRegistrations)return;dt(`Cannot register type '${h}' twice`)}if(hi[i]=s,delete Fr[i],Ii.hasOwnProperty(i)){var d=Ii[i];delete Ii[i],d.forEach(g=>g())}}function fn(i,s,c={}){if(s.argPackAdvance===void 0)throw new TypeError("registerType registeredInstance requires argPackAdvance");return Fu(i,s,c)}var $o=(i,s,c)=>{switch(s){case 1:return c?h=>Ze[h]:h=>ie[h];case 2:return c?h=>Te[h>>1]:h=>Ee[h>>1];case 4:return c?h=>ue[h>>2]:h=>ve[h>>2];case 8:return c?h=>Qe[h>>3]:h=>k[h>>3];default:throw new TypeError(`invalid integer width (${s}): ${i}`)}},di=i=>{if(i===null)return"null";var s=typeof i;return s==="object"||s==="array"||s==="function"?i.toString():""+i},qo=(i,s,c,h)=>{if(s<c||s>h)throw new TypeError(`Passing a number "${di(s)}" from JS side to C/C++ side to an argument of type "${i}", which is outside the valid range [${c}, ${h}]!`)},Uu=(i,s,c,h,d)=>{s=zt(s);const g=h===0n;let T=b=>b;if(g){const b=c*8;T=F=>BigInt.asUintN(b,F),d=T(d)}fn(i,{name:s,fromWireType:T,toWireType:(b,F)=>{if(typeof F=="number")F=BigInt(F);else if(typeof F!="bigint")throw new TypeError(`Cannot convert "${di(F)}" to ${this.name}`);return qo(s,F,h,d),F},argPackAdvance:bn,readValueFromPointer:$o(s,c,!g),destructorFunction:null})},bn=8,Nu=(i,s,c,h)=>{s=zt(s),fn(i,{name:s,fromWireType:function(d){return!!d},toWireType:function(d,g){return g?c:h},argPackAdvance:bn,readValueFromPointer:function(d){return this.fromWireType(ie[d])},destructorFunction:null})},Ou=i=>({count:i.count,deleteScheduled:i.deleteScheduled,preservePointerOnDelete:i.preservePointerOnDelete,ptr:i.ptr,ptrType:i.ptrType,smartPtr:i.smartPtr,smartPtrType:i.smartPtrType}),Ws=i=>{function s(c){return c.$$.ptrType.registeredClass.name}dt(s(i)+" instance already deleted")},Xs=!1,Yo=i=>{},ku=i=>{i.smartPtr?i.smartPtrType.rawDestructor(i.smartPtr):i.ptrType.registeredClass.rawDestructor(i.ptr)},Ko=i=>{i.count.value-=1;var s=i.count.value===0;s&&ku(i)},Zo=(i,s,c)=>{if(s===c)return i;if(c.baseClass===void 0)return null;var h=Zo(i,s,c.baseClass);return h===null?null:c.downcast(h)},Jo={},Bu={},zu=(i,s)=>{for(s===void 0&&dt("ptr should not be undefined");i.baseClass;)s=i.upcast(s),i=i.baseClass;return s},Hu=(i,s)=>(s=zu(i,s),Bu[s]),Vu=class extends Error{constructor(s){super(s),this.name="InternalError"}},Ur=i=>{throw new Vu(i)},Nr=(i,s)=>{(!s.ptrType||!s.ptr)&&Ur("makeClassHandle requires ptr and ptrType");var c=!!s.smartPtrType,h=!!s.smartPtr;return c!==h&&Ur("Both smartPtrType and smartPtr must be specified"),s.count={value:1},hr(Object.create(i,{$$:{value:s,writable:!0}}))};function Qo(i){var s=this.getPointee(i);if(!s)return this.destructor(i),null;var c=Hu(this.registeredClass,s);if(c!==void 0){if(c.$$.count.value===0)return c.$$.ptr=s,c.$$.smartPtr=i,c.clone();var h=c.clone();return this.destructor(i),h}function d(){return this.isSmartPointer?Nr(this.registeredClass.instancePrototype,{ptrType:this.pointeeType,ptr:s,smartPtrType:this,smartPtr:i}):Nr(this.registeredClass.instancePrototype,{ptrType:this,ptr:i})}var g=this.registeredClass.getActualType(s),T=Jo[g];if(!T)return d.call(this);var b;this.isConst?b=T.constPointerType:b=T.pointerType;var F=Zo(s,this.registeredClass,b.registeredClass);return F===null?d.call(this):this.isSmartPointer?Nr(b.registeredClass.instancePrototype,{ptrType:b,ptr:F,smartPtrType:this,smartPtr:i}):Nr(b.registeredClass.instancePrototype,{ptrType:b,ptr:F})}var hr=i=>typeof FinalizationRegistry>"u"?(hr=s=>s,i):(Xs=new FinalizationRegistry(s=>{console.warn(s.leakWarning),Ko(s.$$)}),hr=s=>{var c=s.$$,h=!!c.smartPtr;if(h){var d={$$:c},g=c.ptrType.registeredClass,T=new Error(`Embind found a leaked C++ instance ${g.name} <${Ie(c.ptr)}>.
We'll free it automatically in this case, but this functionality is not reliable across various environments.
Make sure to invoke .delete() manually once you're done with the instance instead.
Originally allocated`);"captureStackTrace"in Error&&Error.captureStackTrace(T,Qo),d.leakWarning=T.stack.replace(/^Error: /,""),Xs.register(s,d,s)}return s},Yo=s=>Xs.unregister(s),hr(i)),Gu=()=>{let i=Or.prototype;Object.assign(i,{isAliasOf(c){if(!(this instanceof Or)||!(c instanceof Or))return!1;var h=this.$$.ptrType.registeredClass,d=this.$$.ptr;c.$$=c.$$;for(var g=c.$$.ptrType.registeredClass,T=c.$$.ptr;h.baseClass;)d=h.upcast(d),h=h.baseClass;for(;g.baseClass;)T=g.upcast(T),g=g.baseClass;return h===g&&d===T},clone(){if(this.$$.ptr||Ws(this),this.$$.preservePointerOnDelete)return this.$$.count.value+=1,this;var c=hr(Object.create(Object.getPrototypeOf(this),{$$:{value:Ou(this.$$)}}));return c.$$.count.value+=1,c.$$.deleteScheduled=!1,c},delete(){this.$$.ptr||Ws(this),this.$$.deleteScheduled&&!this.$$.preservePointerOnDelete&&dt("Object already scheduled for deletion"),Yo(this),Ko(this.$$),this.$$.preservePointerOnDelete||(this.$$.smartPtr=void 0,this.$$.ptr=void 0)},isDeleted(){return!this.$$.ptr},deleteLater(){return this.$$.ptr||Ws(this),this.$$.deleteScheduled&&!this.$$.preservePointerOnDelete&&dt("Object already scheduled for deletion"),this.$$.deleteScheduled=!0,this}});const s=Symbol.dispose;s&&(i[s]=i.delete)};function Or(){}var kr=(i,s)=>Object.defineProperty(s,"name",{value:i}),js=(i,s,c)=>{if(i[s].overloadTable===void 0){var h=i[s];i[s]=function(...d){return i[s].overloadTable.hasOwnProperty(d.length)||dt(`Function '${c}' called with an invalid number of arguments (${d.length}) - expects one of (${i[s].overloadTable})!`),i[s].overloadTable[d.length].apply(this,d)},i[s].overloadTable=[],i[s].overloadTable[h.argCount]=h}},$s=(i,s,c)=>{t.hasOwnProperty(i)?((c===void 0||t[i].overloadTable!==void 0&&t[i].overloadTable[c]!==void 0)&&dt(`Cannot register public name '${i}' twice`),js(t,i,i),t[i].overloadTable.hasOwnProperty(c)&&dt(`Cannot register multiple overloads of a function with the same number of arguments (${c})!`),t[i].overloadTable[c]=s):(t[i]=s,t[i].argCount=c)},Wu=48,Xu=57,ju=i=>{D(typeof i=="string"),i=i.replace(/[^a-zA-Z0-9_]/g,"$");var s=i.charCodeAt(0);return s>=Wu&&s<=Xu?`_${i}`:i};function $u(i,s,c,h,d,g,T,b){this.name=i,this.constructor=s,this.instancePrototype=c,this.rawDestructor=h,this.baseClass=d,this.getActualType=g,this.upcast=T,this.downcast=b,this.pureVirtualFunctions=[]}var Br=(i,s,c)=>{for(;s!==c;)s.upcast||dt(`Expected null or instance of ${c.name}, got an instance of ${s.name}`),i=s.upcast(i),s=s.baseClass;return i};function qu(i,s){if(s===null)return this.isReference&&dt(`null is not a valid ${this.name}`),0;s.$$||dt(`Cannot pass "${di(s)}" as a ${this.name}`),s.$$.ptr||dt(`Cannot pass deleted object as a pointer of type ${this.name}`);var c=s.$$.ptrType.registeredClass,h=Br(s.$$.ptr,c,this.registeredClass);return h}function Yu(i,s){var c;if(s===null)return this.isReference&&dt(`null is not a valid ${this.name}`),this.isSmartPointer?(c=this.rawConstructor(),i!==null&&i.push(this.rawDestructor,c),c):0;(!s||!s.$$)&&dt(`Cannot pass "${di(s)}" as a ${this.name}`),s.$$.ptr||dt(`Cannot pass deleted object as a pointer of type ${this.name}`),!this.isConst&&s.$$.ptrType.isConst&&dt(`Cannot convert argument of type ${s.$$.smartPtrType?s.$$.smartPtrType.name:s.$$.ptrType.name} to parameter type ${this.name}`);var h=s.$$.ptrType.registeredClass;if(c=Br(s.$$.ptr,h,this.registeredClass),this.isSmartPointer)switch(s.$$.smartPtr===void 0&&dt("Passing raw pointer to smart pointer is illegal"),this.sharingPolicy){case 0:s.$$.smartPtrType===this?c=s.$$.smartPtr:dt(`Cannot convert argument of type ${s.$$.smartPtrType?s.$$.smartPtrType.name:s.$$.ptrType.name} to parameter type ${this.name}`);break;case 1:c=s.$$.smartPtr;break;case 2:if(s.$$.smartPtrType===this)c=s.$$.smartPtr;else{var d=s.clone();c=this.rawShare(c,Ht.toHandle(()=>d.delete())),i!==null&&i.push(this.rawDestructor,c)}break;default:dt("Unsupporting sharing policy")}return c}function Ku(i,s){if(s===null)return this.isReference&&dt(`null is not a valid ${this.name}`),0;s.$$||dt(`Cannot pass "${di(s)}" as a ${this.name}`),s.$$.ptr||dt(`Cannot pass deleted object as a pointer of type ${this.name}`),s.$$.ptrType.isConst&&dt(`Cannot convert argument of type ${s.$$.ptrType.name} to parameter type ${this.name}`);var c=s.$$.ptrType.registeredClass,h=Br(s.$$.ptr,c,this.registeredClass);return h}function zr(i){return this.fromWireType(ve[i>>2])}var Zu=()=>{Object.assign(Hr.prototype,{getPointee(i){return this.rawGetPointee&&(i=this.rawGetPointee(i)),i},destructor(i){this.rawDestructor?.(i)},argPackAdvance:bn,readValueFromPointer:zr,fromWireType:Qo})};function Hr(i,s,c,h,d,g,T,b,F,W,K){this.name=i,this.registeredClass=s,this.isReference=c,this.isConst=h,this.isSmartPointer=d,this.pointeeType=g,this.sharingPolicy=T,this.rawGetPointee=b,this.rawConstructor=F,this.rawShare=W,this.rawDestructor=K,!d&&s.baseClass===void 0?h?(this.toWireType=qu,this.destructorFunction=null):(this.toWireType=Ku,this.destructorFunction=null):this.toWireType=Yu}var ec=(i,s,c)=>{t.hasOwnProperty(i)||Ur("Replacing nonexistent public symbol"),t[i].overloadTable!==void 0&&c!==void 0?t[i].overloadTable[c]=s:(t[i]=s,t[i].argCount=c)},tc=[],Vr,ge=i=>{var s=tc[i];return s||(tc[i]=s=Vr.get(i)),D(Vr.get(i)==s,"JavaScript-side Wasm function table mirror is out of date!"),s},wn=(i,s,c=!1)=>{D(!c,"Async bindings are only supported with JSPI."),i=zt(i);function h(){var g=ge(s);return g}var d=h();return typeof d!="function"&&dt(`unknown function pointer with signature ${i}: ${s}`),d};class Ju extends Error{}var nc=i=>{var s=Ec(i),c=zt(s);return Rn(s),c},fi=(i,s)=>{var c=[],h={};function d(g){if(!h[g]&&!hi[g]){if(Fr[g]){Fr[g].forEach(d);return}c.push(g),h[g]=!0}}throw s.forEach(d),new Ju(`${i}: `+c.map(nc).join([", "]))},vn=(i,s,c)=>{i.forEach(b=>Fr[b]=s);function h(b){var F=c(b);F.length!==i.length&&Ur("Mismatched type converter count");for(var W=0;W<i.length;++W)fn(i[W],F[W])}var d=new Array(s.length),g=[],T=0;s.forEach((b,F)=>{hi.hasOwnProperty(b)?d[F]=hi[b]:(g.push(b),Ii.hasOwnProperty(b)||(Ii[b]=[]),Ii[b].push(()=>{d[F]=hi[b],++T,T===g.length&&h(d)}))}),g.length===0&&h(d)},Qu=(i,s,c,h,d,g,T,b,F,W,K,oe,le)=>{K=zt(K),g=wn(d,g),b&&=wn(T,b),W&&=wn(F,W),le=wn(oe,le);var ce=ju(K);$s(ce,function(){fi(`Cannot construct ${K} due to unbound types`,[h])}),vn([i,s,c],h?[h]:[],fe=>{fe=fe[0];var je,ht;h?(je=fe.registeredClass,ht=je.instancePrototype):ht=Or.prototype;var st=kr(K,function(...Tt){if(Object.getPrototypeOf(this)!==Rt)throw new ur(`Use 'new' to construct ${K}`);if(mt.constructor_body===void 0)throw new ur(`${K} has no accessible constructor`);var _i=mt.constructor_body[Tt.length];if(_i===void 0)throw new ur(`Tried to invoke ctor of ${K} with invalid number of parameters (${Tt.length}) - expected (${Object.keys(mt.constructor_body).toString()}) parameters instead!`);return _i.apply(this,Tt)}),Rt=Object.create(ht,{constructor:{value:st}});st.prototype=Rt;var mt=new $u(K,st,Rt,le,je,g,b,W);mt.baseClass&&(mt.baseClass.__derivedClasses??=[],mt.baseClass.__derivedClasses.push(mt));var Zt=new Hr(K,mt,!0,!1,!1),Vt=new Hr(K+"*",mt,!1,!1,!1),tn=new Hr(K+" const*",mt,!1,!0,!1);return Jo[i]={pointerType:Vt,constPointerType:tn},ec(ce,st),[Zt,Vt,tn]})},qs=i=>{for(;i.length;){var s=i.pop(),c=i.pop();c(s)}};function ic(i){for(var s=1;s<i.length;++s)if(i[s]!==null&&i[s].destructorFunction===void 0)return!0;return!1}function eh(i,s,c,h,d){if(i<s||i>c){var g=s==c?s:`${s} to ${c}`;d(`function ${h} called with ${i} arguments, expected ${g}`)}}function th(i,s,c,h){var d=ic(i),g=i.length-2,T=[],b=["fn"];s&&b.push("thisWired");for(var F=0;F<g;++F)T.push(`arg${F}`),b.push(`arg${F}Wired`);T=T.join(","),b=b.join(",");var W=`return function (${T}) {
`;W+=`checkArgCount(arguments.length, minArgs, maxArgs, humanName, throwBindingError);
`,d&&(W+=`var destructors = [];
`);var K=d?"destructors":"null",oe=["humanName","throwBindingError","invoker","fn","runDestructors","retType","classParam"];s&&(W+=`var thisWired = classParam['toWireType'](${K}, this);
`);for(var F=0;F<g;++F)W+=`var arg${F}Wired = argType${F}['toWireType'](${K}, arg${F});
`,oe.push(`argType${F}`);if(W+=(c||h?"var rv = ":"")+`invoker(${b});
`,d)W+=`runDestructors(destructors);
`;else for(var F=s?1:2;F<i.length;++F){var le=F===1?"thisWired":"arg"+(F-2)+"Wired";i[F].destructorFunction!==null&&(W+=`${le}_dtor(${le});
`,oe.push(`${le}_dtor`))}return c&&(W+=`var ret = retType['fromWireType'](rv);
return ret;
`),W+=`}
`,oe.push("checkArgCount","minArgs","maxArgs"),W=`if (arguments.length !== ${oe.length}){ throw new Error(humanName + "Expected ${oe.length} closure arguments " + arguments.length + " given."); }
${W}`,[oe,W]}function nh(i){for(var s=i.length-2,c=i.length-1;c>=2&&i[c].optional;--c)s--;return s}function Gr(i,s,c,h,d,g){var T=s.length;T<2&&dt("argTypes array size mismatch! Must at least get return value and 'this' types!"),D(!g,"Async bindings are only supported with JSPI.");for(var b=s[1]!==null&&c!==null,F=ic(s),W=s[0].name!=="void",K=T-2,oe=nh(s),le=[i,dt,h,d,qs,s[0],s[1]],ce=0;ce<T-2;++ce)le.push(s[ce+2]);if(!F)for(var ce=b?1:2;ce<s.length;++ce)s[ce].destructorFunction!==null&&le.push(s[ce].destructorFunction);le.push(eh,oe,K);let[fe,je]=th(s,b,W,g);var ht=new Function(...fe,je)(...le);return kr(i,ht)}var Wr=(i,s)=>{for(var c=[],h=0;h<i;h++)c.push(ve[s+h*4>>2]);return c},Ys=i=>{i=i.trim();const s=i.indexOf("(");return s===-1?i:(D(i.endsWith(")"),"Parentheses for argument names should match."),i.slice(0,s))},ih=(i,s,c,h,d,g,T,b,F)=>{var W=Wr(c,h);s=zt(s),s=Ys(s),g=wn(d,g,b),vn([],[i],K=>{K=K[0];var oe=`${K.name}.${s}`;function le(){fi(`Cannot call ${oe} due to unbound types`,W)}s.startsWith("@@")&&(s=Symbol[s.substring(2)]);var ce=K.registeredClass.constructor;return ce[s]===void 0?(le.argCount=c-1,ce[s]=le):(js(ce,s,oe),ce[s].overloadTable[c-1]=le),vn([],W,fe=>{var je=[fe[0],null].concat(fe.slice(1)),ht=Gr(oe,je,null,g,T,b);if(ce[s].overloadTable===void 0?(ht.argCount=c-1,ce[s]=ht):ce[s].overloadTable[c-1]=ht,K.registeredClass.__derivedClasses)for(const st of K.registeredClass.__derivedClasses)st.constructor.hasOwnProperty(s)||(st.constructor[s]=ht);return[]}),[]})},rh=(i,s,c,h,d,g)=>{D(s>0);var T=Wr(s,c);d=wn(h,d),vn([],[i],b=>{b=b[0];var F=`constructor ${b.name}`;if(b.registeredClass.constructor_body===void 0&&(b.registeredClass.constructor_body=[]),b.registeredClass.constructor_body[s-1]!==void 0)throw new ur(`Cannot register multiple constructors with identical number of parameters (${s-1}) for class '${b.name}'! Overload resolution is currently only performed using the parameter count, not actual type info!`);return b.registeredClass.constructor_body[s-1]=()=>{fi(`Cannot construct ${b.name} due to unbound types`,T)},vn([],T,W=>(W.splice(1,0,null),b.registeredClass.constructor_body[s-1]=Gr(F,W,null,d,g),[])),[]})},sh=(i,s,c,h,d,g,T,b,F,W)=>{var K=Wr(c,h);s=zt(s),s=Ys(s),g=wn(d,g,F),vn([],[i],oe=>{oe=oe[0];var le=`${oe.name}.${s}`;s.startsWith("@@")&&(s=Symbol[s.substring(2)]),b&&oe.registeredClass.pureVirtualFunctions.push(s);function ce(){fi(`Cannot call ${le} due to unbound types`,K)}var fe=oe.registeredClass.instancePrototype,je=fe[s];return je===void 0||je.overloadTable===void 0&&je.className!==oe.name&&je.argCount===c-2?(ce.argCount=c-2,ce.className=oe.name,fe[s]=ce):(js(fe,s,le),fe[s].overloadTable[c-2]=ce),vn([],K,ht=>{var st=Gr(le,ht,oe,g,T,F);return fe[s].overloadTable===void 0?(st.argCount=c-2,fe[s]=st):fe[s].overloadTable[c-2]=st,[]}),[]})},rc=(i,s,c)=>(i instanceof Object||dt(`${c} with invalid "this": ${i}`),i instanceof s.registeredClass.constructor||dt(`${c} incompatible with "this" of type ${i.constructor.name}`),i.$$.ptr||dt(`cannot call emscripten binding method ${c} on deleted object`),Br(i.$$.ptr,i.$$.ptrType.registeredClass,s.registeredClass)),ah=(i,s,c,h,d,g,T,b,F,W)=>{s=zt(s),d=wn(h,d),vn([],[i],K=>{K=K[0];var oe=`${K.name}.${s}`,le={get(){fi(`Cannot access ${oe} due to unbound types`,[c,T])},enumerable:!0,configurable:!0};return F?le.set=()=>fi(`Cannot access ${oe} due to unbound types`,[c,T]):le.set=ce=>dt(oe+" is a read-only property"),Object.defineProperty(K.registeredClass.instancePrototype,s,le),vn([],F?[c,T]:[c],ce=>{var fe=ce[0],je={get(){var st=rc(this,K,oe+" getter");return fe.fromWireType(d(g,st))},enumerable:!0};if(F){F=wn(b,F);var ht=ce[1];je.set=function(st){var Rt=rc(this,K,oe+" setter"),mt=[];F(W,Rt,ht.toWireType(mt,st)),qs(mt)}}return Object.defineProperty(K.registeredClass.instancePrototype,s,je),[]}),[]})},oh=(i,s,c)=>{i=zt(i),vn([],[s],h=>(h=h[0],t[i]=h.fromWireType(c),[]))},sc=[],An=[0,1,,1,null,1,!0,1,!1,1],Ks=i=>{i>9&&--An[i+1]===0&&(D(An[i]!==void 0,"Decref for unallocated handle."),An[i]=void 0,sc.push(i))},Ht={toValue:i=>(i||dt(`Cannot use deleted val. handle = ${i}`),D(i===2||An[i]!==void 0&&i%2===0,`invalid handle: ${i}`),An[i]),toHandle:i=>{switch(i){case void 0:return 2;case null:return 4;case!0:return 6;case!1:return 8;default:{const s=sc.pop()||An.length;return An[s]=i,An[s+1]=1,s}}}},ac={name:"emscripten::val",fromWireType:i=>{var s=Ht.toValue(i);return Ks(i),s},toWireType:(i,s)=>Ht.toHandle(s),argPackAdvance:bn,readValueFromPointer:zr,destructorFunction:null},oc=i=>fn(i,ac),ch=(i,s,c)=>{switch(s){case 1:return c?function(h){return this.fromWireType(Ze[h])}:function(h){return this.fromWireType(ie[h])};case 2:return c?function(h){return this.fromWireType(Te[h>>1])}:function(h){return this.fromWireType(Ee[h>>1])};case 4:return c?function(h){return this.fromWireType(ue[h>>2])}:function(h){return this.fromWireType(ve[h>>2])};default:throw new TypeError(`invalid integer width (${s}): ${i}`)}},lh=(i,s,c,h)=>{s=zt(s);function d(){}d.values={},fn(i,{name:s,constructor:d,fromWireType:function(g){return this.constructor.values[g]},toWireType:(g,T)=>T.value,argPackAdvance:bn,readValueFromPointer:ch(s,c,h),destructorFunction:null}),$s(s,d)},Xr=(i,s)=>{var c=hi[i];return c===void 0&&dt(`${s} has unknown type ${nc(i)}`),c},uh=(i,s,c)=>{var h=Xr(i,"enum");s=zt(s);var d=h.constructor,g=Object.create(h.constructor.prototype,{value:{value:c},constructor:{value:kr(`${h.name}_${s}`,function(){})}});d.values[c]=g,d[s]=g},hh=(i,s)=>{switch(s){case 4:return function(c){return this.fromWireType(Ye[c>>2])};case 8:return function(c){return this.fromWireType(Ct[c>>3])};default:throw new TypeError(`invalid float width (${s}): ${i}`)}},dh=(i,s,c)=>{s=zt(s),fn(i,{name:s,fromWireType:h=>h,toWireType:(h,d)=>{if(typeof d!="number"&&typeof d!="boolean")throw new TypeError(`Cannot convert ${di(d)} to ${this.name}`);return d},argPackAdvance:bn,readValueFromPointer:hh(s,c),destructorFunction:null})},fh=(i,s,c,h,d,g,T,b)=>{var F=Wr(s,c);i=zt(i),i=Ys(i),d=wn(h,d,T),$s(i,function(){fi(`Cannot call ${i} due to unbound types`,F)},s-1),vn([],F,W=>{var K=[W[0],null].concat(W.slice(1));return ec(i,Gr(i,K,null,d,g,T),s-1),[]})},ph=(i,s,c,h,d)=>{s=zt(s);const g=h===0;let T=F=>F;if(g){var b=32-8*c;T=F=>F<<b>>>b,d=T(d)}fn(i,{name:s,fromWireType:T,toWireType:(F,W)=>{if(typeof W!="number"&&typeof W!="boolean")throw new TypeError(`Cannot convert "${di(W)}" to ${s}`);return qo(s,W,h,d),W},argPackAdvance:bn,readValueFromPointer:$o(s,c,h!==0),destructorFunction:null})},mh=(i,s,c)=>{var h=[Int8Array,Uint8Array,Int16Array,Uint16Array,Int32Array,Uint32Array,Float32Array,Float64Array,BigInt64Array,BigUint64Array],d=h[s];function g(T){var b=ve[T>>2],F=ve[T+4>>2];return new d(Ze.buffer,F,b)}c=zt(c),fn(i,{name:c,fromWireType:g,argPackAdvance:bn,readValueFromPointer:g},{ignoreDuplicateRegistrations:!0})},_h=Object.assign({optional:!0},ac),gh=(i,s)=>{fn(i,_h)},pi=(i,s,c)=>(D(typeof c=="number","stringToUTF8(str, outPtr, maxBytesToWrite) is missing the third parameter that specifies the length of the output buffer!"),Re(i,ie,s,c)),vh=(i,s)=>{s=zt(s),fn(i,{name:s,fromWireType(c){for(var h=ve[c>>2],d=c+4,g,T,b=d,T=0;T<=h;++T){var F=d+T;if(T==h||ie[F]==0){var W=F-b,K=rt(b,W);g===void 0?g=K:(g+="\0",g+=K),b=F+1}}return Rn(c),g},toWireType(c,h){h instanceof ArrayBuffer&&(h=new Uint8Array(h));var d,g=typeof h=="string";g||ArrayBuffer.isView(h)&&h.BYTES_PER_ELEMENT==1||dt("Cannot pass non-string to std::string"),g?d=pe(h):d=h.length;var T=Qs(4+d+1),b=T+4;return ve[T>>2]=d,g?pi(h,b,d+1):ie.set(h,b),c!==null&&c.push(Rn,T),T},argPackAdvance:bn,readValueFromPointer:zr,destructorFunction(c){Rn(c)}})},cc=typeof TextDecoder<"u"?new TextDecoder("utf-16le"):void 0,xh=(i,s)=>{D(i%2==0,"Pointer passed to UTF16ToString must be aligned to two bytes!");for(var c=i>>1,h=c+s/2,d=c;!(d>=h)&&Ee[d];)++d;if(d-c>16&&cc)return cc.decode(Ee.subarray(c,d));for(var g="",T=c;!(T>=h);++T){var b=Ee[T];if(b==0)break;g+=String.fromCharCode(b)}return g},yh=(i,s,c)=>{if(D(s%2==0,"Pointer passed to stringToUTF16 must be aligned to two bytes!"),D(typeof c=="number","stringToUTF16(str, outPtr, maxBytesToWrite) is missing the third parameter that specifies the length of the output buffer!"),c??=2147483647,c<2)return 0;c-=2;for(var h=s,d=c<i.length*2?c/2:i.length,g=0;g<d;++g){var T=i.charCodeAt(g);Te[s>>1]=T,s+=2}return Te[s>>1]=0,s-h},Eh=i=>i.length*2,Sh=(i,s)=>{D(i%4==0,"Pointer passed to UTF32ToString must be aligned to four bytes!");for(var c="",h=0;!(h>=s/4);h++){var d=ue[i+h*4>>2];if(!d)break;c+=String.fromCodePoint(d)}return c},Mh=(i,s,c)=>{if(D(s%4==0,"Pointer passed to stringToUTF32 must be aligned to four bytes!"),D(typeof c=="number","stringToUTF32(str, outPtr, maxBytesToWrite) is missing the third parameter that specifies the length of the output buffer!"),c??=2147483647,c<4)return 0;for(var h=s,d=h+c-4,g=0;g<i.length;++g){var T=i.codePointAt(g);if(T>65535&&g++,ue[s>>2]=T,s+=4,s+4>d)break}return ue[s>>2]=0,s-h},Th=i=>{for(var s=0,c=0;c<i.length;++c){var h=i.codePointAt(c);h>65535&&c++,s+=4}return s},bh=(i,s,c)=>{c=zt(c);var h,d,g,T;s===2?(h=xh,d=yh,T=Eh,g=b=>Ee[b>>1]):s===4&&(h=Sh,d=Mh,T=Th,g=b=>ve[b>>2]),fn(i,{name:c,fromWireType:b=>{for(var F=ve[b>>2],W,K=b+4,oe=0;oe<=F;++oe){var le=b+4+oe*s;if(oe==F||g(le)==0){var ce=le-K,fe=h(K,ce);W===void 0?W=fe:(W+="\0",W+=fe),K=le+s}}return Rn(b),W},toWireType:(b,F)=>{typeof F!="string"&&dt(`Cannot pass non-string to C++ string type ${c}`);var W=T(F),K=Qs(4+W+s);return ve[K>>2]=W/s,d(F,K+4,W+s),b!==null&&b.push(Rn,K),K},argPackAdvance:bn,readValueFromPointer:zr,destructorFunction(b){Rn(b)}})},wh=(i,s)=>{oc(i)},Ah=(i,s)=>{s=zt(s),fn(i,{isVoid:!0,name:s,argPackAdvance:0,fromWireType:()=>{},toWireType:(c,h)=>{}})},Rh=()=>{throw new O},lc=(i,s,c)=>{var h=[],d=i.toWireType(h,c);return h.length&&(ve[s>>2]=Ht.toHandle(h)),d},Ch=(i,s,c)=>(i=Ht.toValue(i),s=Xr(s,"emval::as"),lc(s,c,i)),jr=[],Ph=(i,s,c,h)=>(i=jr[i],s=Ht.toValue(s),i(null,s,c,h)),Dh={},Zs=i=>{var s=Dh[i];return s===void 0?zt(i):s},Lh=(i,s,c,h,d)=>(i=jr[i],s=Ht.toValue(s),c=Zs(c),i(s,s[c],h,d)),uc=()=>globalThis,Ih=i=>i===0?Ht.toHandle(uc()):(i=Zs(i),Ht.toHandle(uc()[i])),Fh=i=>{var s=jr.length;return jr.push(i),s},Uh=(i,s)=>{for(var c=new Array(i),h=0;h<i;++h)c[h]=Xr(ve[s+h*4>>2],`parameter ${h}`);return c},Nh=(i,s,c)=>{var h=Uh(i,s),d=h.shift();i--;var g=`return function (obj, func, destructorsRef, args) {
`,T=0,b=[];c===0&&b.push("obj");for(var F=["retType"],W=[d],K=0;K<i;++K)b.push(`arg${K}`),F.push(`argType${K}`),W.push(h[K]),g+=`  var arg${K} = argType${K}.readValueFromPointer(args${T?"+"+T:""});
`,T+=h[K].argPackAdvance;var oe=c===1?"new func":"func.call";g+=`  var rv = ${oe}(${b.join(", ")});
`,d.isVoid||(F.push("emval_returnValue"),W.push(lc),g+=`  return emval_returnValue(retType, destructorsRef, rv);
`),g+=`};
`;var le=new Function(...F,g)(...W),ce=`methodCaller<(${h.map(fe=>fe.name).join(", ")}) => ${d.name}>`;return Fh(kr(ce,le))},Oh=(i,s)=>(i=Ht.toValue(i),s=Ht.toValue(s),Ht.toHandle(i[s])),kh=i=>{i>9&&(An[i+1]+=1)},Bh=i=>(i=Ht.toValue(i),typeof i=="number"),zh=i=>(i=Ht.toValue(i),typeof i=="string"),Hh=()=>Ht.toHandle([]),Vh=i=>Ht.toHandle(Zs(i)),Gh=i=>{var s=Ht.toValue(i);qs(s),Ks(i)},Wh=(i,s)=>{i=Xr(i,"_emval_take_value");var c=i.readValueFromPointer(s);return Ht.toHandle(c)},Xh=i=>{throw i=Ht.toValue(i),i},jh=i=>i%4===0&&(i%100!==0||i%400===0),$h=[0,31,60,91,121,152,182,213,244,274,305,335],qh=[0,31,59,90,120,151,181,212,243,273,304,334],hc=i=>{var s=jh(i.getFullYear()),c=s?$h:qh,h=c[i.getMonth()]+i.getDate()-1;return h},Yh=9007199254740992,Kh=-9007199254740992,dc=i=>i<Kh||i>Yh?NaN:Number(i);function Zh(i,s){i=dc(i);var c=new Date(i*1e3);ue[s>>2]=c.getSeconds(),ue[s+4>>2]=c.getMinutes(),ue[s+8>>2]=c.getHours(),ue[s+12>>2]=c.getDate(),ue[s+16>>2]=c.getMonth(),ue[s+20>>2]=c.getFullYear()-1900,ue[s+24>>2]=c.getDay();var h=hc(c)|0;ue[s+28>>2]=h,ue[s+36>>2]=-(c.getTimezoneOffset()*60);var d=new Date(c.getFullYear(),0,1),g=new Date(c.getFullYear(),6,1).getTimezoneOffset(),T=d.getTimezoneOffset(),b=(g!=T&&c.getTimezoneOffset()==Math.min(T,g))|0;ue[s+32>>2]=b}var Jh=function(i){var s=(()=>{var c=new Date(ue[i+20>>2]+1900,ue[i+16>>2],ue[i+12>>2],ue[i+8>>2],ue[i+4>>2],ue[i>>2],0),h=ue[i+32>>2],d=c.getTimezoneOffset(),g=new Date(c.getFullYear(),0,1),T=new Date(c.getFullYear(),6,1).getTimezoneOffset(),b=g.getTimezoneOffset(),F=Math.min(b,T);if(h<0)ue[i+32>>2]=+(T!=b&&F==d);else if(h>0!=(F==d)){var W=Math.max(b,T),K=h>0?F:W;c.setTime(c.getTime()+(K-d)*6e4)}ue[i+24>>2]=c.getDay();var oe=hc(c)|0;ue[i+28>>2]=oe,ue[i>>2]=c.getSeconds(),ue[i+4>>2]=c.getMinutes(),ue[i+8>>2]=c.getHours(),ue[i+12>>2]=c.getDate(),ue[i+16>>2]=c.getMonth(),ue[i+20>>2]=c.getYear();var le=c.getTime();return isNaN(le)?-1:le/1e3})();return BigInt(s)},Qh=(i,s,c,h)=>{var d=new Date().getFullYear(),g=new Date(d,0,1),T=new Date(d,6,1),b=g.getTimezoneOffset(),F=T.getTimezoneOffset(),W=Math.max(b,F);ve[i>>2]=W*60,ue[s>>2]=+(b!=F);var K=ce=>{var fe=ce>=0?"-":"+",je=Math.abs(ce),ht=String(Math.floor(je/60)).padStart(2,"0"),st=String(je%60).padStart(2,"0");return`UTC${fe}${ht}${st}`},oe=K(b),le=K(F);D(oe),D(le),D(pe(oe)<=16,`timezone name truncated to fit in TZNAME_MAX (${oe})`),D(pe(le)<=16,`timezone name truncated to fit in TZNAME_MAX (${le})`),F<b?(pi(oe,c,17),pi(le,h,17)):(pi(oe,h,17),pi(le,c,17))},fc=()=>performance.now(),pc=()=>Date.now(),ed=i=>i>=0&&i<=3;function td(i,s,c){if(!ed(i))return 28;var h;i===0?h=pc():h=fc();var d=Math.round(h*1e3*1e3);return Qe[c>>3]=BigInt(d),0}var $r=[],nd=(i,s)=>{D(Array.isArray($r)),D(s%16==0),$r.length=0;for(var c;c=ie[i++];){var h=String.fromCharCode(c),d=["d","f","i","p"];d.push("j"),D(d.includes(h),`Invalid character ${c}("${h}") in readEmAsmArgs! Use only [${d}], and do not specify "v" for void return argument.`);var g=c!=105;g&=c!=112,s+=g&&s%8?4:0,$r.push(c==112?ve[s>>2]:c==106?Qe[s>>3]:c==105?ue[s>>2]:Ct[s>>3]),s+=g?8:4}return $r},id=(i,s,c)=>{var h=nd(s,c);return D(yc.hasOwnProperty(i),`No EM_ASM constant found at address ${i}.  The loaded WebAssembly file is likely out of sync with the generated JavaScript.`),yc[i](...h)},rd=(i,s,c)=>id(i,s,c),mc=()=>2147483648,sd=()=>mc(),ad=(i,s)=>(D(s,"alignment argument is required"),Math.ceil(i/s)*s),od=i=>{var s=xt.buffer,c=(i-s.byteLength+65535)/65536|0;try{return xt.grow(c),We(),1}catch(h){I(`growMemory: Attempted to grow heap from ${s.byteLength} bytes to ${i} bytes, but got error: ${h}`)}},cd=i=>{var s=ie.length;i>>>=0,D(i>s);var c=mc();if(i>c)return I(`Cannot enlarge memory, requested ${i} bytes, but the limit is ${c} bytes!`),!1;for(var h=1;h<=4;h*=2){var d=s*(1+.2/h);d=Math.min(d,i+100663296);var g=Math.min(c,ad(Math.max(i,d),65536)),T=od(g);if(T)return!0}return I(`Failed to grow the heap from ${s} bytes to ${g} bytes, not enough memory!`),!1},Js={},ld=()=>p||"./this.program",dr=()=>{if(!dr.strings){var i=(typeof navigator=="object"&&navigator.language||"C").replace("-","_")+".UTF-8",s={USER:"web_user",LOGNAME:"web_user",PATH:"/",PWD:"/",HOME:"/home/web_user",LANG:i,_:ld()};for(var c in Js)Js[c]===void 0?delete s[c]:s[c]=Js[c];var h=[];for(var c in s)h.push(`${c}=${s[c]}`);dr.strings=h}return dr.strings},ud=(i,s)=>{var c=0,h=0;for(var d of dr()){var g=s+c;ve[i+h>>2]=g,c+=pi(d,g,1/0)+1,h+=4}return 0},hd=(i,s)=>{var c=dr();ve[i>>2]=c.length;var h=0;for(var d of c)h+=pe(d)+1;return ve[s>>2]=h,0},_c=0,gc=()=>be||_c>0,dd=i=>{gc()||(t.onExit?.(i),B=!0),f(i,new $e(i))},fd=(i,s)=>{if(bp(),gc()&&!s){var c=`program exited (with status: ${i}), but keepRuntimeAlive() is set (counter=${_c}) due to an async operation, so halting execution but not exiting the runtime or preventing further async execution (you can use emscripten_force_exit, if you want to force a true shutdown)`;tt?.(c),I(c)}dd(i)},pd=fd;function md(i){try{var s=yt.getStreamFromFD(i);return S.close(s),0}catch(c){if(typeof S>"u"||c.name!=="ErrnoError")throw c;return c.errno}}var _d=(i,s,c,h)=>{for(var d=0,g=0;g<c;g++){var T=ve[s>>2],b=ve[s+4>>2];s+=8;var F=S.read(i,Ze,T,b,h);if(F<0)return-1;if(d+=F,F<b)break}return d};function gd(i,s,c,h){try{var d=yt.getStreamFromFD(i),g=_d(d,s,c);return ve[h>>2]=g,0}catch(T){if(typeof S>"u"||T.name!=="ErrnoError")throw T;return T.errno}}function vd(i,s,c,h){s=dc(s);try{if(isNaN(s))return 61;var d=yt.getStreamFromFD(i);return S.llseek(d,s,c),Qe[h>>3]=BigInt(d.position),d.getdents&&s===0&&c===0&&(d.getdents=null),0}catch(g){if(typeof S>"u"||g.name!=="ErrnoError")throw g;return g.errno}}var xd=(i,s,c,h)=>{for(var d=0,g=0;g<c;g++){var T=ve[s>>2],b=ve[s+4>>2];s+=8;var F=S.write(i,Ze,T,b,h);if(F<0)return-1;if(d+=F,F<b)break}return d};function yd(i,s,c,h){try{var d=yt.getStreamFromFD(i),g=xd(d,s,c);return ve[h>>2]=g,0}catch(T){if(typeof S>"u"||T.name!=="ErrnoError")throw T;return T.errno}}var Ed=i=>i,Sd=i=>{var s=t["_"+i];return D(s,"Cannot call unknown function "+i+", make sure it is exported"),s},Md=(i,s)=>{D(i.length>=0,"writeArrayToMemory array must have a length (should be an array or typed array)"),Ze.set(i,s)},qr=i=>wc(i),Td=i=>{var s=pe(i)+1,c=qr(s);return pi(i,c,s),c},vc=(i,s,c,h,d)=>{var g={string:fe=>{var je=0;return fe!=null&&fe!==0&&(je=Td(fe)),je},array:fe=>{var je=qr(fe.length);return Md(fe,je),je}};function T(fe){return s==="string"?rt(fe):s==="boolean"?!!fe:fe}var b=Sd(i),F=[],W=0;if(D(s!=="array",'Return type should not be "array".'),h)for(var K=0;K<h.length;K++){var oe=g[c[K]];oe?(W===0&&(W=z()),F[K]=oe(h[K])):F[K]=h[K]}var le=b(...F);function ce(fe){return W!==0&&G(W),T(fe)}return le=ce(le),le},bd=(i,s,c,h)=>(...d)=>vc(i,s,c,d),wd=(...i)=>S.createPath(...i),Ad=(...i)=>S.unlink(...i),Rd=(...i)=>S.createLazyFile(...i),Cd=(...i)=>S.createDevice(...i),Pd=i=>Yr(i),Dd=i=>na(i),Ld=i=>{var s=z(),c=qr(4),h=qr(4);Rc(i,c,h);var d=ve[c>>2],g=ve[h>>2],T=rt(d);Rn(d);var b;return g&&(b=rt(g),Rn(g)),G(s),[T,b]},xc=i=>Ld(i);S.createPreloadedFile=Xe,S.staticInit(),Gu(),Zu(),D(An.length===10),t.noExitRuntime&&(be=t.noExitRuntime),t.preloadPlugins&&(Mt=t.preloadPlugins),t.print&&(N=t.print),t.printErr&&(I=t.printErr),t.wasmBinary&&(L=t.wasmBinary),Ud(),t.arguments&&t.arguments,t.thisProgram&&(p=t.thisProgram),D(typeof t.memoryInitializerPrefixURL>"u","Module.memoryInitializerPrefixURL option was removed, use Module.locateFile instead"),D(typeof t.pthreadMainPrefixURL>"u","Module.pthreadMainPrefixURL option was removed, use Module.locateFile instead"),D(typeof t.cdInitializerPrefixURL>"u","Module.cdInitializerPrefixURL option was removed, use Module.locateFile instead"),D(typeof t.filePackagePrefixURL>"u","Module.filePackagePrefixURL option was removed, use Module.locateFile instead"),D(typeof t.read>"u","Module.read option was removed"),D(typeof t.readAsync>"u","Module.readAsync option was removed (modify readAsync in JS)"),D(typeof t.readBinary>"u","Module.readBinary option was removed (modify readBinary in JS)"),D(typeof t.setWindowTitle>"u","Module.setWindowTitle option was removed (modify emscripten_set_window_title in JS)"),D(typeof t.TOTAL_MEMORY>"u","Module.TOTAL_MEMORY has been renamed Module.INITIAL_MEMORY"),D(typeof t.ENVIRONMENT>"u","Module.ENVIRONMENT has been deprecated. To force the environment, use the ENVIRONMENT compile-time option (for example, -sENVIRONMENT=web or -sENVIRONMENT=node)"),D(typeof t.STACK_SIZE>"u","STACK_SIZE can no longer be set at runtime.  Use -sSTACK_SIZE at link time"),D(typeof t.wasmMemory>"u","Use of `wasmMemory` detected.  Use -sIMPORTED_MEMORY to define wasmMemory externally"),D(typeof t.INITIAL_MEMORY>"u","Detected runtime INITIAL_MEMORY setting.  Use -sIMPORTED_MEMORY to define wasmMemory dynamically"),t.addRunDependency=U,t.removeRunDependency=w,t.ccall=vc,t.cwrap=bd,t.FS_createPreloadedFile=Xe,t.FS_unlink=Ad,t.FS_createPath=wd,t.FS_createDevice=Cd,t.FS=S,t.FS_createDataFile=vt,t.FS_createLazyFile=Rd,t.MEMFS=_e;var Id=["writeI53ToI64","writeI53ToI64Clamped","writeI53ToI64Signaling","writeI53ToU64Clamped","writeI53ToU64Signaling","readI53FromI64","readI53FromU64","convertI32PairToI53","convertI32PairToI53Checked","convertU32PairToI53","getTempRet0","zeroMemory","withStackSave","inetPton4","inetNtop4","inetPton6","inetNtop6","readSockaddr","writeSockaddr","emscriptenLog","runMainThreadEmAsm","jstoi_q","autoResumeAudioContext","getDynCaller","dynCall","handleException","runtimeKeepalivePush","runtimeKeepalivePop","callUserCallback","maybeExit","asmjsMangle","HandleAllocator","getNativeTypeSize","addOnInit","addOnPostCtor","addOnPreMain","addOnExit","STACK_SIZE","STACK_ALIGN","POINTER_SIZE","ASSERTIONS","uleb128Encode","sigToWasmTypes","generateFuncType","convertJsFunctionToWasm","getEmptyTableSlot","updateTableMap","getFunctionAddress","addFunction","removeFunction","reallyNegative","unSign","strLen","reSign","formatString","intArrayToString","stringToAscii","stringToNewUTF8","registerKeyEventCallback","maybeCStringToJsString","findEventTarget","getBoundingClientRect","fillMouseEventData","registerMouseEventCallback","registerWheelEventCallback","registerUiEventCallback","registerFocusEventCallback","fillDeviceOrientationEventData","registerDeviceOrientationEventCallback","fillDeviceMotionEventData","registerDeviceMotionEventCallback","screenOrientation","fillOrientationChangeEventData","registerOrientationChangeEventCallback","fillFullscreenChangeEventData","registerFullscreenChangeEventCallback","JSEvents_requestFullscreen","JSEvents_resizeCanvasForFullscreen","registerRestoreOldStyle","hideEverythingExceptGivenElement","restoreHiddenElements","setLetterbox","softFullscreenResizeWebGLRenderTarget","doRequestFullscreen","fillPointerlockChangeEventData","registerPointerlockChangeEventCallback","registerPointerlockErrorEventCallback","requestPointerLock","fillVisibilityChangeEventData","registerVisibilityChangeEventCallback","registerTouchEventCallback","fillGamepadEventData","registerGamepadEventCallback","registerBeforeUnloadEventCallback","fillBatteryEventData","battery","registerBatteryEventCallback","setCanvasElementSize","getCanvasElementSize","jsStackTrace","getCallstack","convertPCtoSourceLocation","wasiRightsToMuslOFlags","wasiOFlagsToMuslOFlags","safeSetTimeout","setImmediateWrapped","safeRequestAnimationFrame","clearImmediateWrapped","registerPostMainLoop","registerPreMainLoop","getPromise","makePromise","idsToPromises","makePromiseCallback","Browser_asyncPrepareDataCounter","arraySum","addDays","getSocketFromFD","getSocketAddress","FS_mkdirTree","_setNetworkCallback","heapObjectForWebGLType","toTypedArrayIndex","webgl_enable_ANGLE_instanced_arrays","webgl_enable_OES_vertex_array_object","webgl_enable_WEBGL_draw_buffers","webgl_enable_WEBGL_multi_draw","webgl_enable_EXT_polygon_offset_clamp","webgl_enable_EXT_clip_control","webgl_enable_WEBGL_polygon_mode","emscriptenWebGLGet","computeUnpackAlignedImageSize","colorChannelsInGlTextureFormat","emscriptenWebGLGetTexPixelData","emscriptenWebGLGetUniform","webglGetUniformLocation","webglPrepareUniformLocationsBeforeFirstUse","webglGetLeftBracePos","emscriptenWebGLGetVertexAttrib","__glGetActiveAttribOrUniform","writeGLArray","registerWebGlEventCallback","runAndAbortIfError","ALLOC_NORMAL","ALLOC_STACK","allocate","writeStringToMemory","writeAsciiToMemory","demangle","stackTrace","getFunctionArgsName","createJsInvokerSignature","PureVirtualError","registerInheritedInstance","unregisterInheritedInstance","getInheritedInstanceCount","getLiveInheritedInstances","setDelayFunction","count_emval_handles"];Id.forEach(Ae);var Fd=["run","out","err","callMain","abort","wasmMemory","wasmExports","HEAPF32","HEAPF64","HEAP8","HEAPU8","HEAP16","HEAPU16","HEAP32","HEAPU32","HEAP64","HEAPU64","writeStackCookie","checkStackCookie","INT53_MAX","INT53_MIN","bigintToI53Checked","stackSave","stackRestore","stackAlloc","setTempRet0","ptrToString","exitJS","getHeapMax","growMemory","ENV","ERRNO_CODES","strError","DNS","Protocols","Sockets","timers","warnOnce","readEmAsmArgsArray","readEmAsmArgs","runEmAsmFunction","getExecutableName","keepRuntimeAlive","asyncLoad","alignMemory","mmapAlloc","wasmTable","getUniqueRunDependency","noExitRuntime","addOnPreRun","addOnPostRun","freeTableIndexes","functionsInTableMap","setValue","getValue","PATH","PATH_FS","UTF8Decoder","UTF8ArrayToString","UTF8ToString","stringToUTF8Array","stringToUTF8","lengthBytesUTF8","intArrayFromString","AsciiToString","UTF16Decoder","UTF16ToString","stringToUTF16","lengthBytesUTF16","UTF32ToString","stringToUTF32","lengthBytesUTF32","stringToUTF8OnStack","writeArrayToMemory","JSEvents","specialHTMLTargets","findCanvasEventTarget","currentFullscreenStrategy","restoreOldWindowedStyle","UNWIND_CACHE","ExitStatus","getEnvStrings","checkWasiClock","doReadv","doWritev","initRandomFill","randomFill","emSetImmediate","emClearImmediate_deps","emClearImmediate","promiseMap","uncaughtExceptionCount","exceptionLast","exceptionCaught","ExceptionInfo","findMatchingCatch","getExceptionMessageCommon","Browser","requestFullscreen","requestFullScreen","setCanvasSize","getUserMedia","createContext","getPreloadedImageData__data","wget","MONTH_DAYS_REGULAR","MONTH_DAYS_LEAP","MONTH_DAYS_REGULAR_CUMULATIVE","MONTH_DAYS_LEAP_CUMULATIVE","isLeapYear","ydayFromDate","SYSCALLS","preloadPlugins","FS_modeStringToFlags","FS_getMode","FS_stdin_getChar_buffer","FS_stdin_getChar","FS_readFile","FS_root","FS_mounts","FS_devices","FS_streams","FS_nextInode","FS_nameTable","FS_currentPath","FS_initialized","FS_ignorePermissions","FS_filesystems","FS_syncFSRequests","FS_readFiles","FS_lookupPath","FS_getPath","FS_hashName","FS_hashAddNode","FS_hashRemoveNode","FS_lookupNode","FS_createNode","FS_destroyNode","FS_isRoot","FS_isMountpoint","FS_isFile","FS_isDir","FS_isLink","FS_isChrdev","FS_isBlkdev","FS_isFIFO","FS_isSocket","FS_flagsToPermissionString","FS_nodePermissions","FS_mayLookup","FS_mayCreate","FS_mayDelete","FS_mayOpen","FS_checkOpExists","FS_nextfd","FS_getStreamChecked","FS_getStream","FS_createStream","FS_closeStream","FS_dupStream","FS_doSetAttr","FS_chrdev_stream_ops","FS_major","FS_minor","FS_makedev","FS_registerDevice","FS_getDevice","FS_getMounts","FS_syncfs","FS_mount","FS_unmount","FS_lookup","FS_mknod","FS_statfs","FS_statfsStream","FS_statfsNode","FS_create","FS_mkdir","FS_mkdev","FS_symlink","FS_rename","FS_rmdir","FS_readdir","FS_readlink","FS_stat","FS_fstat","FS_lstat","FS_doChmod","FS_chmod","FS_lchmod","FS_fchmod","FS_doChown","FS_chown","FS_lchown","FS_fchown","FS_doTruncate","FS_truncate","FS_ftruncate","FS_utime","FS_open","FS_close","FS_isClosed","FS_llseek","FS_read","FS_write","FS_mmap","FS_msync","FS_ioctl","FS_writeFile","FS_cwd","FS_chdir","FS_createDefaultDirectories","FS_createDefaultDevices","FS_createSpecialDirectories","FS_createStandardStreams","FS_staticInit","FS_init","FS_quit","FS_findObject","FS_analyzePath","FS_createFile","FS_forceLoadFile","FS_absolutePath","FS_createFolder","FS_createLink","FS_joinPath","FS_mmapAlloc","FS_standardizePath","TTY","PIPEFS","SOCKFS","tempFixedLengthArray","miniTempWebGLFloatBuffers","miniTempWebGLIntBuffers","GL","AL","GLUT","EGL","GLEW","IDBStore","SDL","SDL_gfx","allocateUTF8","allocateUTF8OnStack","print","printErr","jstoi_s","InternalError","BindingError","throwInternalError","throwBindingError","registeredTypes","awaitingDependencies","typeDependencies","tupleRegistrations","structRegistrations","sharedRegisterType","whenDependentTypesAreResolved","getTypeName","getFunctionName","heap32VectorToArray","requireRegisteredType","usesDestructorStack","checkArgCount","getRequiredArgCount","createJsInvoker","UnboundTypeError","GenericWireTypeSize","EmValType","EmValOptionalType","throwUnboundTypeError","ensureOverloadTable","exposePublicSymbol","replacePublicSymbol","createNamedFunction","embindRepr","registeredInstances","getBasestPointer","getInheritedInstance","registeredPointers","registerType","integerReadValueFromPointer","enumReadValueFromPointer","floatReadValueFromPointer","assertIntegerRange","readPointer","runDestructors","craftInvokerFunction","embind__requireFunction","genericPointerToWireType","constNoSmartPtrRawPointerToWireType","nonConstNoSmartPtrRawPointerToWireType","init_RegisteredPointer","RegisteredPointer","RegisteredPointer_fromWireType","runDestructor","releaseClassHandle","finalizationRegistry","detachFinalizer_deps","detachFinalizer","attachFinalizer","makeClassHandle","init_ClassHandle","ClassHandle","throwInstanceAlreadyDeleted","deletionQueue","flushPendingDeletes","delayFunction","RegisteredClass","shallowCopyInternalPointer","downcastPointer","upcastPointer","validateThis","char_0","char_9","makeLegalFunctionName","emval_freelist","emval_handles","emval_symbols","getStringOrSymbol","Emval","emval_get_global","emval_returnValue","emval_lookupTypes","emval_methodCallers","emval_addMethodCaller"];Fd.forEach(De),t.incrementExceptionRefcount=Pd,t.decrementExceptionRefcount=Dd,t.getExceptionMessage=xc;function Ud(){he("fetchSettings")}var yc={658116:()=>{typeof t<"u"&&"mjDISABLESTRING mjENABLESTRING mjFRAMESTRING mjLABELSTRING mjRNDSTRING mjTIMERSTRING mjVISSTRING".split(" ").forEach(function(i){Object.defineProperty(t,i,{get:function(){return t["get_"+i]()},set:function(s){},enumerable:!0,configurable:!0})})}},Ec=Z("___getTypeName"),Qs=Z("_malloc"),ea=Z("_fflush"),Rn=Z("_free"),ta=Z("_emscripten_stack_get_end"),Sc=Z("_strerror"),me=Z("_setThrew"),Mc=Z("__emscripten_tempret_set"),Tc=Z("_emscripten_stack_init"),bc=Z("__emscripten_stack_restore"),wc=Z("__emscripten_stack_alloc"),Ac=Z("_emscripten_stack_get_current"),na=Z("___cxa_decrement_exception_refcount"),Yr=Z("___cxa_increment_exception_refcount"),Rc=Z("___get_exception_message"),Cc=Z("___cxa_can_catch"),Pc=Z("___cxa_get_exception_ptr");function Nd(i){Ec=ne("__getTypeName",1),Qs=ne("malloc",1),ea=ne("fflush",1),Rn=ne("free",1),ta=i.emscripten_stack_get_end,i.emscripten_stack_get_base,Sc=ne("strerror",1),me=ne("setThrew",2),Mc=ne("_emscripten_tempret_set",1),Tc=i.emscripten_stack_init,i.emscripten_stack_get_free,bc=i._emscripten_stack_restore,wc=i._emscripten_stack_alloc,Ac=i.emscripten_stack_get_current,na=ne("__cxa_decrement_exception_refcount",1),Yr=ne("__cxa_increment_exception_refcount",1),Rc=ne("__get_exception_message",3),Cc=ne("__cxa_can_catch",3),Pc=ne("__cxa_get_exception_ptr",1)}var Dc={__assert_fail:gn,__cxa_begin_catch:Un,__cxa_current_primary_exception:cr,__cxa_end_catch:Pr,__cxa_find_matching_catch_2:Dr,__cxa_find_matching_catch_3:Lr,__cxa_find_matching_catch_4:Bs,__cxa_rethrow:Ir,__cxa_rethrow_primary_exception:zs,__cxa_throw:Hs,__cxa_uncaught_exceptions:Vs,__resumeException:Gs,__syscall_dup3:Lt,__syscall_fcntl64:Yt,__syscall_fstat64:Kt,__syscall_ioctl:lr,__syscall_lstat64:kn,__syscall_newfstatat:Pu,__syscall_openat:Du,__syscall_stat64:Lu,_abort_js:Iu,_embind_register_bigint:Uu,_embind_register_bool:Nu,_embind_register_class:Qu,_embind_register_class_class_function:ih,_embind_register_class_constructor:rh,_embind_register_class_function:sh,_embind_register_class_property:ah,_embind_register_constant:oh,_embind_register_emval:oc,_embind_register_enum:lh,_embind_register_enum_value:uh,_embind_register_float:dh,_embind_register_function:fh,_embind_register_integer:ph,_embind_register_memory_view:mh,_embind_register_optional:gh,_embind_register_std_string:vh,_embind_register_std_wstring:bh,_embind_register_user_type:wh,_embind_register_void:Ah,_emscripten_throw_longjmp:Rh,_emval_as:Ch,_emval_call:Ph,_emval_call_method:Lh,_emval_decref:Ks,_emval_get_global:Ih,_emval_get_method_caller:Nh,_emval_get_property:Oh,_emval_incref:kh,_emval_is_number:Bh,_emval_is_string:zh,_emval_new_array:Hh,_emval_new_cstring:Vh,_emval_run_destructors:Gh,_emval_take_value:Wh,_emval_throw:Xh,_localtime_js:Zh,_mktime_js:Jh,_tzset_js:Qh,clock_time_get:td,emscripten_asm_const_int:rd,emscripten_date_now:pc,emscripten_get_heap_max:sd,emscripten_get_now:fc,emscripten_resize_heap:cd,environ_get:ud,environ_sizes_get:hd,exit:pd,fd_close:md,fd_read:gd,fd_seek:vd,fd_write:yd,invoke_ddd:up,invoke_dddi:Af,invoke_dddidi:Rf,invoke_ddidi:wf,invoke_di:Cf,invoke_dii:gf,invoke_diii:Kd,invoke_diiii:bf,invoke_diiiidd:Mf,invoke_diiiidi:Qd,invoke_diiiii:Xd,invoke_diiiiii:af,invoke_diiiiiii:Pf,invoke_diiiiiiiii:rf,invoke_diiiiiiiiiiii:sf,invoke_fiii:Ep,invoke_i:jd,invoke_id:sp,invoke_ii:Bd,invoke_iid:zf,invoke_iidddd:mp,invoke_iidiii:pf,invoke_iidiiid:df,invoke_iidiiiiidi:mf,invoke_iif:pp,invoke_iii:Od,invoke_iiid:_f,invoke_iiididdddddd:ff,invoke_iiidiiiiiiii:hf,invoke_iiii:Vd,invoke_iiiidddiiiii:Lf,invoke_iiiii:Yd,invoke_iiiiid:Kf,invoke_iiiiii:Xf,invoke_iiiiiii:Vf,invoke_iiiiiiii:Bf,invoke_iiiiiiiidd:Zf,invoke_iiiiiiiii:Sf,invoke_iiiiiiiiii:Gf,invoke_iiiiiiiiiidddiiiiiiiii:uf,invoke_iiiiiiiiiii:yp,invoke_iiiiiiiiiiii:Sp,invoke_iiiiiiiiiiiii:rp,invoke_iiij:Wf,invoke_iiji:Yf,invoke_j:vp,invoke_ji:ip,invoke_jiiii:jf,invoke_jij:np,invoke_v:Hd,invoke_vi:zd,invoke_vid:Hf,invoke_viddd:$f,invoke_vidddd:qf,invoke_vidi:Tf,invoke_vidiii:cf,invoke_vii:Wd,invoke_viid:yf,invoke_viiddi:tp,invoke_viiddidi:ep,invoke_viiddii:Df,invoke_viidi:xf,invoke_viidii:Jd,invoke_viidiii:Of,invoke_viidiiid:Uf,invoke_viidiiiii:lf,invoke_viidiiiiidi:kf,invoke_viidiiiiiiii:of,invoke_viii:kd,invoke_viiid:tf,invoke_viiidd:Qf,invoke_viiidi:vf,invoke_viiididdddddd:Nf,invoke_viiidiiiiiiii:Ff,invoke_viiii:qd,invoke_viiiiddd:Jf,invoke_viiiidi:hp,invoke_viiiifi:dp,invoke_viiiii:Gd,invoke_viiiiid:ef,invoke_viiiiii:$d,invoke_viiiiiii:Zd,invoke_viiiiiiii:Ef,invoke_viiiiiiiiii:cp,invoke_viiiiiiiiiidddiiiiiiiii:If,invoke_viiiiiiiiiiid:nf,invoke_viiiiiiiiiiiii:op,invoke_viiiiiiiiiiiiiii:Mp,invoke_viiiiiiiiiiiiiiiiii:lp,invoke_viiiij:_p,invoke_viij:gp,invoke_viijii:xp,invoke_vij:fp,invoke_vijjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj:ap,llvm_eh_typeid_for:Ed},mi=await Pe();function Od(i,s,c){var h=z();try{return ge(i)(s,c)}catch(d){if(G(h),!(d instanceof M))throw d;me(1,0)}}function kd(i,s,c,h){var d=z();try{ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function Bd(i,s){var c=z();try{return ge(i)(s)}catch(h){if(G(c),!(h instanceof M))throw h;me(1,0)}}function zd(i,s){var c=z();try{ge(i)(s)}catch(h){if(G(c),!(h instanceof M))throw h;me(1,0)}}function Hd(i){var s=z();try{ge(i)()}catch(c){if(G(s),!(c instanceof M))throw c;me(1,0)}}function Vd(i,s,c,h){var d=z();try{return ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function Gd(i,s,c,h,d,g){var T=z();try{ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function Wd(i,s,c){var h=z();try{ge(i)(s,c)}catch(d){if(G(h),!(d instanceof M))throw d;me(1,0)}}function Xd(i,s,c,h,d,g){var T=z();try{return ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function jd(i){var s=z();try{return ge(i)()}catch(c){if(G(s),!(c instanceof M))throw c;me(1,0)}}function $d(i,s,c,h,d,g,T){var b=z();try{ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function qd(i,s,c,h,d){var g=z();try{ge(i)(s,c,h,d)}catch(T){if(G(g),!(T instanceof M))throw T;me(1,0)}}function Yd(i,s,c,h,d){var g=z();try{return ge(i)(s,c,h,d)}catch(T){if(G(g),!(T instanceof M))throw T;me(1,0)}}function Kd(i,s,c,h){var d=z();try{return ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function Zd(i,s,c,h,d,g,T,b){var F=z();try{ge(i)(s,c,h,d,g,T,b)}catch(W){if(G(F),!(W instanceof M))throw W;me(1,0)}}function Jd(i,s,c,h,d,g){var T=z();try{ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function Qd(i,s,c,h,d,g,T){var b=z();try{return ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function ef(i,s,c,h,d,g,T){var b=z();try{ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function tf(i,s,c,h,d){var g=z();try{ge(i)(s,c,h,d)}catch(T){if(G(g),!(T instanceof M))throw T;me(1,0)}}function nf(i,s,c,h,d,g,T,b,F,W,K,oe,le){var ce=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le)}catch(fe){if(G(ce),!(fe instanceof M))throw fe;me(1,0)}}function rf(i,s,c,h,d,g,T,b,F,W){var K=z();try{return ge(i)(s,c,h,d,g,T,b,F,W)}catch(oe){if(G(K),!(oe instanceof M))throw oe;me(1,0)}}function sf(i,s,c,h,d,g,T,b,F,W,K,oe,le){var ce=z();try{return ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le)}catch(fe){if(G(ce),!(fe instanceof M))throw fe;me(1,0)}}function af(i,s,c,h,d,g,T){var b=z();try{return ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function of(i,s,c,h,d,g,T,b,F,W,K,oe){var le=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K,oe)}catch(ce){if(G(le),!(ce instanceof M))throw ce;me(1,0)}}function cf(i,s,c,h,d,g){var T=z();try{ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function lf(i,s,c,h,d,g,T,b,F){var W=z();try{ge(i)(s,c,h,d,g,T,b,F)}catch(K){if(G(W),!(K instanceof M))throw K;me(1,0)}}function uf(i,s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je,ht,st,Rt,mt,Zt,Vt){var tn=z();try{return ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je,ht,st,Rt,mt,Zt,Vt)}catch(Tt){if(G(tn),!(Tt instanceof M))throw Tt;me(1,0)}}function hf(i,s,c,h,d,g,T,b,F,W,K,oe){var le=z();try{return ge(i)(s,c,h,d,g,T,b,F,W,K,oe)}catch(ce){if(G(le),!(ce instanceof M))throw ce;me(1,0)}}function df(i,s,c,h,d,g,T){var b=z();try{return ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function ff(i,s,c,h,d,g,T,b,F,W,K,oe){var le=z();try{return ge(i)(s,c,h,d,g,T,b,F,W,K,oe)}catch(ce){if(G(le),!(ce instanceof M))throw ce;me(1,0)}}function pf(i,s,c,h,d,g){var T=z();try{return ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function mf(i,s,c,h,d,g,T,b,F,W){var K=z();try{return ge(i)(s,c,h,d,g,T,b,F,W)}catch(oe){if(G(K),!(oe instanceof M))throw oe;me(1,0)}}function _f(i,s,c,h){var d=z();try{return ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function gf(i,s,c){var h=z();try{return ge(i)(s,c)}catch(d){if(G(h),!(d instanceof M))throw d;me(1,0)}}function vf(i,s,c,h,d,g){var T=z();try{ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function xf(i,s,c,h,d){var g=z();try{ge(i)(s,c,h,d)}catch(T){if(G(g),!(T instanceof M))throw T;me(1,0)}}function yf(i,s,c,h){var d=z();try{ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function Ef(i,s,c,h,d,g,T,b,F){var W=z();try{ge(i)(s,c,h,d,g,T,b,F)}catch(K){if(G(W),!(K instanceof M))throw K;me(1,0)}}function Sf(i,s,c,h,d,g,T,b,F){var W=z();try{return ge(i)(s,c,h,d,g,T,b,F)}catch(K){if(G(W),!(K instanceof M))throw K;me(1,0)}}function Mf(i,s,c,h,d,g,T){var b=z();try{return ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function Tf(i,s,c,h){var d=z();try{ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function bf(i,s,c,h,d){var g=z();try{return ge(i)(s,c,h,d)}catch(T){if(G(g),!(T instanceof M))throw T;me(1,0)}}function wf(i,s,c,h,d){var g=z();try{return ge(i)(s,c,h,d)}catch(T){if(G(g),!(T instanceof M))throw T;me(1,0)}}function Af(i,s,c,h){var d=z();try{return ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function Rf(i,s,c,h,d,g){var T=z();try{return ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function Cf(i,s){var c=z();try{return ge(i)(s)}catch(h){if(G(c),!(h instanceof M))throw h;me(1,0)}}function Pf(i,s,c,h,d,g,T,b){var F=z();try{return ge(i)(s,c,h,d,g,T,b)}catch(W){if(G(F),!(W instanceof M))throw W;me(1,0)}}function Df(i,s,c,h,d,g,T){var b=z();try{ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function Lf(i,s,c,h,d,g,T,b,F,W,K,oe){var le=z();try{return ge(i)(s,c,h,d,g,T,b,F,W,K,oe)}catch(ce){if(G(le),!(ce instanceof M))throw ce;me(1,0)}}function If(i,s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je,ht,st,Rt,mt,Zt,Vt,tn){var Tt=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je,ht,st,Rt,mt,Zt,Vt,tn)}catch(_i){if(G(Tt),!(_i instanceof M))throw _i;me(1,0)}}function Ff(i,s,c,h,d,g,T,b,F,W,K,oe,le){var ce=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le)}catch(fe){if(G(ce),!(fe instanceof M))throw fe;me(1,0)}}function Uf(i,s,c,h,d,g,T,b){var F=z();try{ge(i)(s,c,h,d,g,T,b)}catch(W){if(G(F),!(W instanceof M))throw W;me(1,0)}}function Nf(i,s,c,h,d,g,T,b,F,W,K,oe,le){var ce=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le)}catch(fe){if(G(ce),!(fe instanceof M))throw fe;me(1,0)}}function Of(i,s,c,h,d,g,T){var b=z();try{ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function kf(i,s,c,h,d,g,T,b,F,W,K){var oe=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K)}catch(le){if(G(oe),!(le instanceof M))throw le;me(1,0)}}function Bf(i,s,c,h,d,g,T,b){var F=z();try{return ge(i)(s,c,h,d,g,T,b)}catch(W){if(G(F),!(W instanceof M))throw W;me(1,0)}}function zf(i,s,c){var h=z();try{return ge(i)(s,c)}catch(d){if(G(h),!(d instanceof M))throw d;me(1,0)}}function Hf(i,s,c){var h=z();try{ge(i)(s,c)}catch(d){if(G(h),!(d instanceof M))throw d;me(1,0)}}function Vf(i,s,c,h,d,g,T){var b=z();try{return ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function Gf(i,s,c,h,d,g,T,b,F,W){var K=z();try{return ge(i)(s,c,h,d,g,T,b,F,W)}catch(oe){if(G(K),!(oe instanceof M))throw oe;me(1,0)}}function Wf(i,s,c,h){var d=z();try{return ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function Xf(i,s,c,h,d,g){var T=z();try{return ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function jf(i,s,c,h,d){var g=z();try{return ge(i)(s,c,h,d)}catch(T){if(G(g),!(T instanceof M))throw T;return me(1,0),0n}}function $f(i,s,c,h,d){var g=z();try{ge(i)(s,c,h,d)}catch(T){if(G(g),!(T instanceof M))throw T;me(1,0)}}function qf(i,s,c,h,d,g){var T=z();try{ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function Yf(i,s,c,h){var d=z();try{return ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function Kf(i,s,c,h,d,g){var T=z();try{return ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function Zf(i,s,c,h,d,g,T,b,F,W){var K=z();try{return ge(i)(s,c,h,d,g,T,b,F,W)}catch(oe){if(G(K),!(oe instanceof M))throw oe;me(1,0)}}function Jf(i,s,c,h,d,g,T,b){var F=z();try{ge(i)(s,c,h,d,g,T,b)}catch(W){if(G(F),!(W instanceof M))throw W;me(1,0)}}function Qf(i,s,c,h,d,g){var T=z();try{ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function ep(i,s,c,h,d,g,T,b){var F=z();try{ge(i)(s,c,h,d,g,T,b)}catch(W){if(G(F),!(W instanceof M))throw W;me(1,0)}}function tp(i,s,c,h,d,g){var T=z();try{ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function np(i,s,c){var h=z();try{return ge(i)(s,c)}catch(d){if(G(h),!(d instanceof M))throw d;return me(1,0),0n}}function ip(i,s){var c=z();try{return ge(i)(s)}catch(h){if(G(c),!(h instanceof M))throw h;return me(1,0),0n}}function rp(i,s,c,h,d,g,T,b,F,W,K,oe,le){var ce=z();try{return ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le)}catch(fe){if(G(ce),!(fe instanceof M))throw fe;me(1,0)}}function sp(i,s){var c=z();try{return ge(i)(s)}catch(h){if(G(c),!(h instanceof M))throw h;me(1,0)}}function ap(i,s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je,ht,st,Rt,mt,Zt,Vt,tn,Tt,_i,Ap,Rp,Cp,Pp,Dp,Lp,Ip,Fp,Up,Np,Op,kp,Bp,zp,Hp,Vp,Gp,Wp,Xp,jp,$p,qp,Yp,Kp,Zp,Jp,Qp,em,tm,nm,im,rm,sm,am,om,cm,lm,um,hm,dm,fm,pm,mm,_m,gm,vm,xm,ym,Em,Sm,Mm,Tm,bm,wm,Am,Rm,Cm,Pm,Dm,Lm,Im){var Fm=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je,ht,st,Rt,mt,Zt,Vt,tn,Tt,_i,Ap,Rp,Cp,Pp,Dp,Lp,Ip,Fp,Up,Np,Op,kp,Bp,zp,Hp,Vp,Gp,Wp,Xp,jp,$p,qp,Yp,Kp,Zp,Jp,Qp,em,tm,nm,im,rm,sm,am,om,cm,lm,um,hm,dm,fm,pm,mm,_m,gm,vm,xm,ym,Em,Sm,Mm,Tm,bm,wm,Am,Rm,Cm,Pm,Dm,Lm,Im)}catch(Ic){if(G(Fm),!(Ic instanceof M))throw Ic;me(1,0)}}function op(i,s,c,h,d,g,T,b,F,W,K,oe,le,ce){var fe=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le,ce)}catch(je){if(G(fe),!(je instanceof M))throw je;me(1,0)}}function cp(i,s,c,h,d,g,T,b,F,W,K){var oe=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K)}catch(le){if(G(oe),!(le instanceof M))throw le;me(1,0)}}function lp(i,s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je,ht,st,Rt){var mt=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je,ht,st,Rt)}catch(Zt){if(G(mt),!(Zt instanceof M))throw Zt;me(1,0)}}function up(i,s,c){var h=z();try{return ge(i)(s,c)}catch(d){if(G(h),!(d instanceof M))throw d;me(1,0)}}function hp(i,s,c,h,d,g,T){var b=z();try{ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function dp(i,s,c,h,d,g,T){var b=z();try{ge(i)(s,c,h,d,g,T)}catch(F){if(G(b),!(F instanceof M))throw F;me(1,0)}}function fp(i,s,c){var h=z();try{ge(i)(s,c)}catch(d){if(G(h),!(d instanceof M))throw d;me(1,0)}}function pp(i,s,c){var h=z();try{return ge(i)(s,c)}catch(d){if(G(h),!(d instanceof M))throw d;me(1,0)}}function mp(i,s,c,h,d,g){var T=z();try{return ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function _p(i,s,c,h,d,g){var T=z();try{ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function gp(i,s,c,h){var d=z();try{ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function vp(i){var s=z();try{return ge(i)()}catch(c){if(G(s),!(c instanceof M))throw c;return me(1,0),0n}}function xp(i,s,c,h,d,g){var T=z();try{ge(i)(s,c,h,d,g)}catch(b){if(G(T),!(b instanceof M))throw b;me(1,0)}}function yp(i,s,c,h,d,g,T,b,F,W,K){var oe=z();try{return ge(i)(s,c,h,d,g,T,b,F,W,K)}catch(le){if(G(oe),!(le instanceof M))throw le;me(1,0)}}function Ep(i,s,c,h){var d=z();try{return ge(i)(s,c,h)}catch(g){if(G(d),!(g instanceof M))throw g;me(1,0)}}function Sp(i,s,c,h,d,g,T,b,F,W,K,oe){var le=z();try{return ge(i)(s,c,h,d,g,T,b,F,W,K,oe)}catch(ce){if(G(le),!(ce instanceof M))throw ce;me(1,0)}}function Mp(i,s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je){var ht=z();try{ge(i)(s,c,h,d,g,T,b,F,W,K,oe,le,ce,fe,je)}catch(st){if(G(ht),!(st instanceof M))throw st;me(1,0)}}var Lc;function Tp(){Tc(),q()}function ia(){if(Le>0){Je=ia;return}if(Tp(),ft(),Le>0){Je=ia;return}function i(){D(!Lc),Lc=!0,t.calledRun=!0,!B&&(Ge(),Ve?.(t),t.onRuntimeInitialized?.(),ee("onRuntimeInitialized"),D(!t._main,'compiled without a main, but one is present. if you added it from JS, use Module["onRuntimeInitialized"]'),At())}t.setStatus?(t.setStatus("Running..."),setTimeout(()=>{setTimeout(()=>t.setStatus(""),1),i()},1)):i(),P()}function bp(){var i=N,s=I,c=!1;N=I=h=>{c=!0};try{ea(0),["stdout","stderr"].forEach(h=>{var d=S.analyzePath("/dev/"+h);if(d){var g=d.object,T=g.rdev,b=He.ttys[T];b?.output?.length&&(c=!0)}})}catch{}N=i,I=s,c&&Fe("stdio streams had content in them that was not flushed. you should set EXIT_RUNTIME to 1 (see the Emscripten FAQ), or make sure to emit a newline when you printf etc.")}function wp(){if(t.preInit)for(typeof t.preInit=="function"&&(t.preInit=[t.preInit]);t.preInit.length>0;)t.preInit.shift()();ee("preInit")}wp(),ia(),_t?e=t:e=new Promise((i,s)=>{Ve=i,tt=s});for(const i of Object.keys(t))i in r||Object.defineProperty(r,i,{configurable:!0,get(){Y(`Access to module property ('${i}') is no longer possible via the module constructor argument; Instead, use the result of the module constructor.`)}});return e});const Zi={ROTATE:0,DOLLY:1,PAN:2},Yi={ROTATE:0,PAN:1,DOLLY_PAN:2,DOLLY_ROTATE:3},Bm=0,Uc=1,zm=2,Xl=1,jl=2,Wn=3,oi=0,an=1,Xn=2,si=0,Ji=1,Nc=2,Oc=3,kc=4,Hm=5,Ti=100,Vm=101,Gm=102,Wm=103,Xm=104,jm=200,$m=201,qm=202,Ym=203,Ha=204,Va=205,Km=206,Zm=207,Jm=208,Qm=209,e_=210,t_=211,n_=212,i_=213,r_=214,Ga=0,Wa=1,Xa=2,tr=3,ja=4,$a=5,qa=6,Ya=7,$l=0,s_=1,a_=2,ai=0,o_=1,c_=2,l_=3,ql=4,u_=5,h_=6,d_=7,Yl=300,nr=301,ir=302,Ka=303,Za=304,Fs=306,Ja=1e3,wi=1001,Qa=1002,Tn=1003,f_=1004,Kr=1005,Pn=1006,ra=1007,Ai=1008,In=1009,Kl=1010,Zl=1011,Sr=1012,Do=1013,Ri=1014,jn=1015,wr=1016,Lo=1017,Io=1018,Mr=1020,Jl=35902,Ql=1021,eu=1022,Mn=1023,Tr=1026,br=1027,tu=1028,Fo=1029,nu=1030,Uo=1031,No=1033,Ss=33776,Ms=33777,Ts=33778,bs=33779,eo=35840,to=35841,no=35842,io=35843,ro=36196,so=37492,ao=37496,oo=37808,co=37809,lo=37810,uo=37811,ho=37812,fo=37813,po=37814,mo=37815,_o=37816,go=37817,vo=37818,xo=37819,yo=37820,Eo=37821,ws=36492,So=36494,Mo=36495,iu=36283,To=36284,bo=36285,wo=36286,p_=3200,m_=3201,ru=0,__=1,ni="",hn="srgb",rr="srgb-linear",Cs="linear",bt="srgb",Fi=7680,Bc=519,g_=512,v_=513,x_=514,su=515,y_=516,E_=517,S_=518,M_=519,zc=35044,Hc="300 es",Dn=2e3,Ps=2001;class Li{addEventListener(e,t){this._listeners===void 0&&(this._listeners={});const n=this._listeners;n[e]===void 0&&(n[e]=[]),n[e].indexOf(t)===-1&&n[e].push(t)}hasEventListener(e,t){const n=this._listeners;return n===void 0?!1:n[e]!==void 0&&n[e].indexOf(t)!==-1}removeEventListener(e,t){const n=this._listeners;if(n===void 0)return;const a=n[e];if(a!==void 0){const o=a.indexOf(t);o!==-1&&a.splice(o,1)}}dispatchEvent(e){const t=this._listeners;if(t===void 0)return;const n=t[e.type];if(n!==void 0){e.target=this;const a=n.slice(0);for(let o=0,l=a.length;o<l;o++)a[o].call(this,e);e.target=null}}}const Jt=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"],As=Math.PI/180,Ao=180/Math.PI;function Ar(){const r=Math.random()*4294967295|0,e=Math.random()*4294967295|0,t=Math.random()*4294967295|0,n=Math.random()*4294967295|0;return(Jt[r&255]+Jt[r>>8&255]+Jt[r>>16&255]+Jt[r>>24&255]+"-"+Jt[e&255]+Jt[e>>8&255]+"-"+Jt[e>>16&15|64]+Jt[e>>24&255]+"-"+Jt[t&63|128]+Jt[t>>8&255]+"-"+Jt[t>>16&255]+Jt[t>>24&255]+Jt[n&255]+Jt[n>>8&255]+Jt[n>>16&255]+Jt[n>>24&255]).toLowerCase()}function lt(r,e,t){return Math.max(e,Math.min(t,r))}function T_(r,e){return(r%e+e)%e}function sa(r,e,t){return(1-t)*r+t*e}function fr(r,e){switch(e.constructor){case Float32Array:return r;case Uint32Array:return r/4294967295;case Uint16Array:return r/65535;case Uint8Array:return r/255;case Int32Array:return Math.max(r/2147483647,-1);case Int16Array:return Math.max(r/32767,-1);case Int8Array:return Math.max(r/127,-1);default:throw new Error("Invalid component type.")}}function rn(r,e){switch(e.constructor){case Float32Array:return r;case Uint32Array:return Math.round(r*4294967295);case Uint16Array:return Math.round(r*65535);case Uint8Array:return Math.round(r*255);case Int32Array:return Math.round(r*2147483647);case Int16Array:return Math.round(r*32767);case Int8Array:return Math.round(r*127);default:throw new Error("Invalid component type.")}}const b_={DEG2RAD:As};class et{constructor(e=0,t=0){et.prototype.isVector2=!0,this.x=e,this.y=t}get width(){return this.x}set width(e){this.x=e}get height(){return this.y}set height(e){this.y=e}set(e,t){return this.x=e,this.y=t,this}setScalar(e){return this.x=e,this.y=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y)}copy(e){return this.x=e.x,this.y=e.y,this}add(e){return this.x+=e.x,this.y+=e.y,this}addScalar(e){return this.x+=e,this.y+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this}subScalar(e){return this.x-=e,this.y-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this}multiply(e){return this.x*=e.x,this.y*=e.y,this}multiplyScalar(e){return this.x*=e,this.y*=e,this}divide(e){return this.x/=e.x,this.y/=e.y,this}divideScalar(e){return this.multiplyScalar(1/e)}applyMatrix3(e){const t=this.x,n=this.y,a=e.elements;return this.x=a[0]*t+a[3]*n+a[6],this.y=a[1]*t+a[4]*n+a[7],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this}clamp(e,t){return this.x=lt(this.x,e.x,t.x),this.y=lt(this.y,e.y,t.y),this}clampScalar(e,t){return this.x=lt(this.x,e,t),this.y=lt(this.y,e,t),this}clampLength(e,t){const n=this.length();return this.divideScalar(n||1).multiplyScalar(lt(n,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(e){return this.x*e.x+this.y*e.y}cross(e){return this.x*e.y-this.y*e.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(e){const t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;const n=this.dot(e)/t;return Math.acos(lt(n,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){const t=this.x-e.x,n=this.y-e.y;return t*t+n*n}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this}equals(e){return e.x===this.x&&e.y===this.y}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this}rotateAround(e,t){const n=Math.cos(t),a=Math.sin(t),o=this.x-e.x,l=this.y-e.y;return this.x=o*n-l*a+e.x,this.y=o*a+l*n+e.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}}class Ci{constructor(e=0,t=0,n=0,a=1){this.isQuaternion=!0,this._x=e,this._y=t,this._z=n,this._w=a}static slerpFlat(e,t,n,a,o,l,u){let p=n[a+0],f=n[a+1],_=n[a+2],v=n[a+3];const x=o[l+0],E=o[l+1],R=o[l+2],C=o[l+3];if(u===0){e[t+0]=p,e[t+1]=f,e[t+2]=_,e[t+3]=v;return}if(u===1){e[t+0]=x,e[t+1]=E,e[t+2]=R,e[t+3]=C;return}if(v!==C||p!==x||f!==E||_!==R){let y=1-u;const m=p*x+f*E+_*R+v*C,N=m>=0?1:-1,I=1-m*m;if(I>Number.EPSILON){const B=Math.sqrt(I),D=Math.atan2(B,m*N);y=Math.sin(y*D)/B,u=Math.sin(u*D)/B}const L=u*N;if(p=p*y+x*L,f=f*y+E*L,_=_*y+R*L,v=v*y+C*L,y===1-u){const B=1/Math.sqrt(p*p+f*f+_*_+v*v);p*=B,f*=B,_*=B,v*=B}}e[t]=p,e[t+1]=f,e[t+2]=_,e[t+3]=v}static multiplyQuaternionsFlat(e,t,n,a,o,l){const u=n[a],p=n[a+1],f=n[a+2],_=n[a+3],v=o[l],x=o[l+1],E=o[l+2],R=o[l+3];return e[t]=u*R+_*v+p*E-f*x,e[t+1]=p*R+_*x+f*v-u*E,e[t+2]=f*R+_*E+u*x-p*v,e[t+3]=_*R-u*v-p*x-f*E,e}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get w(){return this._w}set w(e){this._w=e,this._onChangeCallback()}set(e,t,n,a){return this._x=e,this._y=t,this._z=n,this._w=a,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(e){return this._x=e.x,this._y=e.y,this._z=e.z,this._w=e.w,this._onChangeCallback(),this}setFromEuler(e,t=!0){const n=e._x,a=e._y,o=e._z,l=e._order,u=Math.cos,p=Math.sin,f=u(n/2),_=u(a/2),v=u(o/2),x=p(n/2),E=p(a/2),R=p(o/2);switch(l){case"XYZ":this._x=x*_*v+f*E*R,this._y=f*E*v-x*_*R,this._z=f*_*R+x*E*v,this._w=f*_*v-x*E*R;break;case"YXZ":this._x=x*_*v+f*E*R,this._y=f*E*v-x*_*R,this._z=f*_*R-x*E*v,this._w=f*_*v+x*E*R;break;case"ZXY":this._x=x*_*v-f*E*R,this._y=f*E*v+x*_*R,this._z=f*_*R+x*E*v,this._w=f*_*v-x*E*R;break;case"ZYX":this._x=x*_*v-f*E*R,this._y=f*E*v+x*_*R,this._z=f*_*R-x*E*v,this._w=f*_*v+x*E*R;break;case"YZX":this._x=x*_*v+f*E*R,this._y=f*E*v+x*_*R,this._z=f*_*R-x*E*v,this._w=f*_*v-x*E*R;break;case"XZY":this._x=x*_*v-f*E*R,this._y=f*E*v-x*_*R,this._z=f*_*R+x*E*v,this._w=f*_*v+x*E*R;break;default:console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: "+l)}return t===!0&&this._onChangeCallback(),this}setFromAxisAngle(e,t){const n=t/2,a=Math.sin(n);return this._x=e.x*a,this._y=e.y*a,this._z=e.z*a,this._w=Math.cos(n),this._onChangeCallback(),this}setFromRotationMatrix(e){const t=e.elements,n=t[0],a=t[4],o=t[8],l=t[1],u=t[5],p=t[9],f=t[2],_=t[6],v=t[10],x=n+u+v;if(x>0){const E=.5/Math.sqrt(x+1);this._w=.25/E,this._x=(_-p)*E,this._y=(o-f)*E,this._z=(l-a)*E}else if(n>u&&n>v){const E=2*Math.sqrt(1+n-u-v);this._w=(_-p)/E,this._x=.25*E,this._y=(a+l)/E,this._z=(o+f)/E}else if(u>v){const E=2*Math.sqrt(1+u-n-v);this._w=(o-f)/E,this._x=(a+l)/E,this._y=.25*E,this._z=(p+_)/E}else{const E=2*Math.sqrt(1+v-n-u);this._w=(l-a)/E,this._x=(o+f)/E,this._y=(p+_)/E,this._z=.25*E}return this._onChangeCallback(),this}setFromUnitVectors(e,t){let n=e.dot(t)+1;return n<1e-8?(n=0,Math.abs(e.x)>Math.abs(e.z)?(this._x=-e.y,this._y=e.x,this._z=0,this._w=n):(this._x=0,this._y=-e.z,this._z=e.y,this._w=n)):(this._x=e.y*t.z-e.z*t.y,this._y=e.z*t.x-e.x*t.z,this._z=e.x*t.y-e.y*t.x,this._w=n),this.normalize()}angleTo(e){return 2*Math.acos(Math.abs(lt(this.dot(e),-1,1)))}rotateTowards(e,t){const n=this.angleTo(e);if(n===0)return this;const a=Math.min(1,t/n);return this.slerp(e,a),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(e){return this._x*e._x+this._y*e._y+this._z*e._z+this._w*e._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let e=this.length();return e===0?(this._x=0,this._y=0,this._z=0,this._w=1):(e=1/e,this._x=this._x*e,this._y=this._y*e,this._z=this._z*e,this._w=this._w*e),this._onChangeCallback(),this}multiply(e){return this.multiplyQuaternions(this,e)}premultiply(e){return this.multiplyQuaternions(e,this)}multiplyQuaternions(e,t){const n=e._x,a=e._y,o=e._z,l=e._w,u=t._x,p=t._y,f=t._z,_=t._w;return this._x=n*_+l*u+a*f-o*p,this._y=a*_+l*p+o*u-n*f,this._z=o*_+l*f+n*p-a*u,this._w=l*_-n*u-a*p-o*f,this._onChangeCallback(),this}slerp(e,t){if(t===0)return this;if(t===1)return this.copy(e);const n=this._x,a=this._y,o=this._z,l=this._w;let u=l*e._w+n*e._x+a*e._y+o*e._z;if(u<0?(this._w=-e._w,this._x=-e._x,this._y=-e._y,this._z=-e._z,u=-u):this.copy(e),u>=1)return this._w=l,this._x=n,this._y=a,this._z=o,this;const p=1-u*u;if(p<=Number.EPSILON){const E=1-t;return this._w=E*l+t*this._w,this._x=E*n+t*this._x,this._y=E*a+t*this._y,this._z=E*o+t*this._z,this.normalize(),this}const f=Math.sqrt(p),_=Math.atan2(f,u),v=Math.sin((1-t)*_)/f,x=Math.sin(t*_)/f;return this._w=l*v+this._w*x,this._x=n*v+this._x*x,this._y=a*v+this._y*x,this._z=o*v+this._z*x,this._onChangeCallback(),this}slerpQuaternions(e,t,n){return this.copy(e).slerp(t,n)}random(){const e=2*Math.PI*Math.random(),t=2*Math.PI*Math.random(),n=Math.random(),a=Math.sqrt(1-n),o=Math.sqrt(n);return this.set(a*Math.sin(e),a*Math.cos(e),o*Math.sin(t),o*Math.cos(t))}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._w===this._w}fromArray(e,t=0){return this._x=e[t],this._y=e[t+1],this._z=e[t+2],this._w=e[t+3],this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._w,e}fromBufferAttribute(e,t){return this._x=e.getX(t),this._y=e.getY(t),this._z=e.getZ(t),this._w=e.getW(t),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}}class X{constructor(e=0,t=0,n=0){X.prototype.isVector3=!0,this.x=e,this.y=t,this.z=n}set(e,t,n){return n===void 0&&(n=this.z),this.x=e,this.y=t,this.z=n,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this}multiplyVectors(e,t){return this.x=e.x*t.x,this.y=e.y*t.y,this.z=e.z*t.z,this}applyEuler(e){return this.applyQuaternion(Vc.setFromEuler(e))}applyAxisAngle(e,t){return this.applyQuaternion(Vc.setFromAxisAngle(e,t))}applyMatrix3(e){const t=this.x,n=this.y,a=this.z,o=e.elements;return this.x=o[0]*t+o[3]*n+o[6]*a,this.y=o[1]*t+o[4]*n+o[7]*a,this.z=o[2]*t+o[5]*n+o[8]*a,this}applyNormalMatrix(e){return this.applyMatrix3(e).normalize()}applyMatrix4(e){const t=this.x,n=this.y,a=this.z,o=e.elements,l=1/(o[3]*t+o[7]*n+o[11]*a+o[15]);return this.x=(o[0]*t+o[4]*n+o[8]*a+o[12])*l,this.y=(o[1]*t+o[5]*n+o[9]*a+o[13])*l,this.z=(o[2]*t+o[6]*n+o[10]*a+o[14])*l,this}applyQuaternion(e){const t=this.x,n=this.y,a=this.z,o=e.x,l=e.y,u=e.z,p=e.w,f=2*(l*a-u*n),_=2*(u*t-o*a),v=2*(o*n-l*t);return this.x=t+p*f+l*v-u*_,this.y=n+p*_+u*f-o*v,this.z=a+p*v+o*_-l*f,this}project(e){return this.applyMatrix4(e.matrixWorldInverse).applyMatrix4(e.projectionMatrix)}unproject(e){return this.applyMatrix4(e.projectionMatrixInverse).applyMatrix4(e.matrixWorld)}transformDirection(e){const t=this.x,n=this.y,a=this.z,o=e.elements;return this.x=o[0]*t+o[4]*n+o[8]*a,this.y=o[1]*t+o[5]*n+o[9]*a,this.z=o[2]*t+o[6]*n+o[10]*a,this.normalize()}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this}divideScalar(e){return this.multiplyScalar(1/e)}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this}clamp(e,t){return this.x=lt(this.x,e.x,t.x),this.y=lt(this.y,e.y,t.y),this.z=lt(this.z,e.z,t.z),this}clampScalar(e,t){return this.x=lt(this.x,e,t),this.y=lt(this.y,e,t),this.z=lt(this.z,e,t),this}clampLength(e,t){const n=this.length();return this.divideScalar(n||1).multiplyScalar(lt(n,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this.z=e.z+(t.z-e.z)*n,this}cross(e){return this.crossVectors(this,e)}crossVectors(e,t){const n=e.x,a=e.y,o=e.z,l=t.x,u=t.y,p=t.z;return this.x=a*p-o*u,this.y=o*l-n*p,this.z=n*u-a*l,this}projectOnVector(e){const t=e.lengthSq();if(t===0)return this.set(0,0,0);const n=e.dot(this)/t;return this.copy(e).multiplyScalar(n)}projectOnPlane(e){return aa.copy(this).projectOnVector(e),this.sub(aa)}reflect(e){return this.sub(aa.copy(e).multiplyScalar(2*this.dot(e)))}angleTo(e){const t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;const n=this.dot(e)/t;return Math.acos(lt(n,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){const t=this.x-e.x,n=this.y-e.y,a=this.z-e.z;return t*t+n*n+a*a}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)+Math.abs(this.z-e.z)}setFromSpherical(e){return this.setFromSphericalCoords(e.radius,e.phi,e.theta)}setFromSphericalCoords(e,t,n){const a=Math.sin(t)*e;return this.x=a*Math.sin(n),this.y=Math.cos(t)*e,this.z=a*Math.cos(n),this}setFromCylindrical(e){return this.setFromCylindricalCoords(e.radius,e.theta,e.y)}setFromCylindricalCoords(e,t,n){return this.x=e*Math.sin(t),this.y=n,this.z=e*Math.cos(t),this}setFromMatrixPosition(e){const t=e.elements;return this.x=t[12],this.y=t[13],this.z=t[14],this}setFromMatrixScale(e){const t=this.setFromMatrixColumn(e,0).length(),n=this.setFromMatrixColumn(e,1).length(),a=this.setFromMatrixColumn(e,2).length();return this.x=t,this.y=n,this.z=a,this}setFromMatrixColumn(e,t){return this.fromArray(e.elements,t*4)}setFromMatrix3Column(e,t){return this.fromArray(e.elements,t*3)}setFromEuler(e){return this.x=e._x,this.y=e._y,this.z=e._z,this}setFromColor(e){return this.x=e.r,this.y=e.g,this.z=e.b,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){const e=Math.random()*Math.PI*2,t=Math.random()*2-1,n=Math.sqrt(1-t*t);return this.x=n*Math.cos(e),this.y=t,this.z=n*Math.sin(e),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}}const aa=new X,Vc=new Ci;class it{constructor(e,t,n,a,o,l,u,p,f){it.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],e!==void 0&&this.set(e,t,n,a,o,l,u,p,f)}set(e,t,n,a,o,l,u,p,f){const _=this.elements;return _[0]=e,_[1]=a,_[2]=u,_[3]=t,_[4]=o,_[5]=p,_[6]=n,_[7]=l,_[8]=f,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(e){const t=this.elements,n=e.elements;return t[0]=n[0],t[1]=n[1],t[2]=n[2],t[3]=n[3],t[4]=n[4],t[5]=n[5],t[6]=n[6],t[7]=n[7],t[8]=n[8],this}extractBasis(e,t,n){return e.setFromMatrix3Column(this,0),t.setFromMatrix3Column(this,1),n.setFromMatrix3Column(this,2),this}setFromMatrix4(e){const t=e.elements;return this.set(t[0],t[4],t[8],t[1],t[5],t[9],t[2],t[6],t[10]),this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){const n=e.elements,a=t.elements,o=this.elements,l=n[0],u=n[3],p=n[6],f=n[1],_=n[4],v=n[7],x=n[2],E=n[5],R=n[8],C=a[0],y=a[3],m=a[6],N=a[1],I=a[4],L=a[7],B=a[2],D=a[5],H=a[8];return o[0]=l*C+u*N+p*B,o[3]=l*y+u*I+p*D,o[6]=l*m+u*L+p*H,o[1]=f*C+_*N+v*B,o[4]=f*y+_*I+v*D,o[7]=f*m+_*L+v*H,o[2]=x*C+E*N+R*B,o[5]=x*y+E*I+R*D,o[8]=x*m+E*L+R*H,this}multiplyScalar(e){const t=this.elements;return t[0]*=e,t[3]*=e,t[6]*=e,t[1]*=e,t[4]*=e,t[7]*=e,t[2]*=e,t[5]*=e,t[8]*=e,this}determinant(){const e=this.elements,t=e[0],n=e[1],a=e[2],o=e[3],l=e[4],u=e[5],p=e[6],f=e[7],_=e[8];return t*l*_-t*u*f-n*o*_+n*u*p+a*o*f-a*l*p}invert(){const e=this.elements,t=e[0],n=e[1],a=e[2],o=e[3],l=e[4],u=e[5],p=e[6],f=e[7],_=e[8],v=_*l-u*f,x=u*p-_*o,E=f*o-l*p,R=t*v+n*x+a*E;if(R===0)return this.set(0,0,0,0,0,0,0,0,0);const C=1/R;return e[0]=v*C,e[1]=(a*f-_*n)*C,e[2]=(u*n-a*l)*C,e[3]=x*C,e[4]=(_*t-a*p)*C,e[5]=(a*o-u*t)*C,e[6]=E*C,e[7]=(n*p-f*t)*C,e[8]=(l*t-n*o)*C,this}transpose(){let e;const t=this.elements;return e=t[1],t[1]=t[3],t[3]=e,e=t[2],t[2]=t[6],t[6]=e,e=t[5],t[5]=t[7],t[7]=e,this}getNormalMatrix(e){return this.setFromMatrix4(e).invert().transpose()}transposeIntoArray(e){const t=this.elements;return e[0]=t[0],e[1]=t[3],e[2]=t[6],e[3]=t[1],e[4]=t[4],e[5]=t[7],e[6]=t[2],e[7]=t[5],e[8]=t[8],this}setUvTransform(e,t,n,a,o,l,u){const p=Math.cos(o),f=Math.sin(o);return this.set(n*p,n*f,-n*(p*l+f*u)+l+e,-a*f,a*p,-a*(-f*l+p*u)+u+t,0,0,1),this}scale(e,t){return this.premultiply(oa.makeScale(e,t)),this}rotate(e){return this.premultiply(oa.makeRotation(-e)),this}translate(e,t){return this.premultiply(oa.makeTranslation(e,t)),this}makeTranslation(e,t){return e.isVector2?this.set(1,0,e.x,0,1,e.y,0,0,1):this.set(1,0,e,0,1,t,0,0,1),this}makeRotation(e){const t=Math.cos(e),n=Math.sin(e);return this.set(t,-n,0,n,t,0,0,0,1),this}makeScale(e,t){return this.set(e,0,0,0,t,0,0,0,1),this}equals(e){const t=this.elements,n=e.elements;for(let a=0;a<9;a++)if(t[a]!==n[a])return!1;return!0}fromArray(e,t=0){for(let n=0;n<9;n++)this.elements[n]=e[n+t];return this}toArray(e=[],t=0){const n=this.elements;return e[t]=n[0],e[t+1]=n[1],e[t+2]=n[2],e[t+3]=n[3],e[t+4]=n[4],e[t+5]=n[5],e[t+6]=n[6],e[t+7]=n[7],e[t+8]=n[8],e}clone(){return new this.constructor().fromArray(this.elements)}}const oa=new it;function au(r){for(let e=r.length-1;e>=0;--e)if(r[e]>=65535)return!0;return!1}function Ds(r){return document.createElementNS("http://www.w3.org/1999/xhtml",r)}function w_(){const r=Ds("canvas");return r.style.display="block",r}const Gc={};function Qi(r){r in Gc||(Gc[r]=!0,console.warn(r))}function A_(r,e,t){return new Promise(function(n,a){function o(){switch(r.clientWaitSync(e,r.SYNC_FLUSH_COMMANDS_BIT,0)){case r.WAIT_FAILED:a();break;case r.TIMEOUT_EXPIRED:setTimeout(o,t);break;default:n()}}setTimeout(o,t)})}const Wc=new it().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),Xc=new it().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);function R_(){const r={enabled:!0,workingColorSpace:rr,spaces:{},convert:function(a,o,l){return this.enabled===!1||o===l||!o||!l||(this.spaces[o].transfer===bt&&(a.r=$n(a.r),a.g=$n(a.g),a.b=$n(a.b)),this.spaces[o].primaries!==this.spaces[l].primaries&&(a.applyMatrix3(this.spaces[o].toXYZ),a.applyMatrix3(this.spaces[l].fromXYZ)),this.spaces[l].transfer===bt&&(a.r=er(a.r),a.g=er(a.g),a.b=er(a.b))),a},workingToColorSpace:function(a,o){return this.convert(a,this.workingColorSpace,o)},colorSpaceToWorking:function(a,o){return this.convert(a,o,this.workingColorSpace)},getPrimaries:function(a){return this.spaces[a].primaries},getTransfer:function(a){return a===ni?Cs:this.spaces[a].transfer},getLuminanceCoefficients:function(a,o=this.workingColorSpace){return a.fromArray(this.spaces[o].luminanceCoefficients)},define:function(a){Object.assign(this.spaces,a)},_getMatrix:function(a,o,l){return a.copy(this.spaces[o].toXYZ).multiply(this.spaces[l].fromXYZ)},_getDrawingBufferColorSpace:function(a){return this.spaces[a].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(a=this.workingColorSpace){return this.spaces[a].workingColorSpaceConfig.unpackColorSpace},fromWorkingColorSpace:function(a,o){return Qi("THREE.ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace()."),r.workingToColorSpace(a,o)},toWorkingColorSpace:function(a,o){return Qi("THREE.ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking()."),r.colorSpaceToWorking(a,o)}},e=[.64,.33,.3,.6,.15,.06],t=[.2126,.7152,.0722],n=[.3127,.329];return r.define({[rr]:{primaries:e,whitePoint:n,transfer:Cs,toXYZ:Wc,fromXYZ:Xc,luminanceCoefficients:t,workingColorSpaceConfig:{unpackColorSpace:hn},outputColorSpaceConfig:{drawingBufferColorSpace:hn}},[hn]:{primaries:e,whitePoint:n,transfer:bt,toXYZ:Wc,fromXYZ:Xc,luminanceCoefficients:t,outputColorSpaceConfig:{drawingBufferColorSpace:hn}}}),r}const gt=R_();function $n(r){return r<.04045?r*.0773993808:Math.pow(r*.9478672986+.0521327014,2.4)}function er(r){return r<.0031308?r*12.92:1.055*Math.pow(r,.41666)-.055}let Ui;class C_{static getDataURL(e,t="image/png"){if(/^data:/i.test(e.src)||typeof HTMLCanvasElement>"u")return e.src;let n;if(e instanceof HTMLCanvasElement)n=e;else{Ui===void 0&&(Ui=Ds("canvas")),Ui.width=e.width,Ui.height=e.height;const a=Ui.getContext("2d");e instanceof ImageData?a.putImageData(e,0,0):a.drawImage(e,0,0,e.width,e.height),n=Ui}return n.toDataURL(t)}static sRGBToLinear(e){if(typeof HTMLImageElement<"u"&&e instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&e instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&e instanceof ImageBitmap){const t=Ds("canvas");t.width=e.width,t.height=e.height;const n=t.getContext("2d");n.drawImage(e,0,0,e.width,e.height);const a=n.getImageData(0,0,e.width,e.height),o=a.data;for(let l=0;l<o.length;l++)o[l]=$n(o[l]/255)*255;return n.putImageData(a,0,0),t}else if(e.data){const t=e.data.slice(0);for(let n=0;n<t.length;n++)t instanceof Uint8Array||t instanceof Uint8ClampedArray?t[n]=Math.floor($n(t[n]/255)*255):t[n]=$n(t[n]);return{data:t,width:e.width,height:e.height}}else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),e}}let P_=0;class Oo{constructor(e=null){this.isSource=!0,Object.defineProperty(this,"id",{value:P_++}),this.uuid=Ar(),this.data=e,this.dataReady=!0,this.version=0}getSize(e){const t=this.data;return t instanceof HTMLVideoElement?e.set(t.videoWidth,t.videoHeight,0):t instanceof VideoFrame?e.set(t.displayHeight,t.displayWidth,0):t!==null?e.set(t.width,t.height,t.depth||0):e.set(0,0,0),e}set needsUpdate(e){e===!0&&this.version++}toJSON(e){const t=e===void 0||typeof e=="string";if(!t&&e.images[this.uuid]!==void 0)return e.images[this.uuid];const n={uuid:this.uuid,url:""},a=this.data;if(a!==null){let o;if(Array.isArray(a)){o=[];for(let l=0,u=a.length;l<u;l++)a[l].isDataTexture?o.push(ca(a[l].image)):o.push(ca(a[l]))}else o=ca(a);n.url=o}return t||(e.images[this.uuid]=n),n}}function ca(r){return typeof HTMLImageElement<"u"&&r instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&r instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&r instanceof ImageBitmap?C_.getDataURL(r):r.data?{data:Array.from(r.data),width:r.width,height:r.height,type:r.data.constructor.name}:(console.warn("THREE.Texture: Unable to serialize Texture."),{})}let D_=0;const la=new X;class on extends Li{constructor(e=on.DEFAULT_IMAGE,t=on.DEFAULT_MAPPING,n=wi,a=wi,o=Pn,l=Ai,u=Mn,p=In,f=on.DEFAULT_ANISOTROPY,_=ni){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:D_++}),this.uuid=Ar(),this.name="",this.source=new Oo(e),this.mipmaps=[],this.mapping=t,this.channel=0,this.wrapS=n,this.wrapT=a,this.magFilter=o,this.minFilter=l,this.anisotropy=f,this.format=u,this.internalFormat=null,this.type=p,this.offset=new et(0,0),this.repeat=new et(1,1),this.center=new et(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new it,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=_,this.userData={},this.updateRanges=[],this.version=0,this.onUpdate=null,this.renderTarget=null,this.isRenderTargetTexture=!1,this.isArrayTexture=!!(e&&e.depth&&e.depth>1),this.pmremVersion=0}get width(){return this.source.getSize(la).x}get height(){return this.source.getSize(la).y}get depth(){return this.source.getSize(la).z}get image(){return this.source.data}set image(e=null){this.source.data=e}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}clone(){return new this.constructor().copy(this)}copy(e){return this.name=e.name,this.source=e.source,this.mipmaps=e.mipmaps.slice(0),this.mapping=e.mapping,this.channel=e.channel,this.wrapS=e.wrapS,this.wrapT=e.wrapT,this.magFilter=e.magFilter,this.minFilter=e.minFilter,this.anisotropy=e.anisotropy,this.format=e.format,this.internalFormat=e.internalFormat,this.type=e.type,this.offset.copy(e.offset),this.repeat.copy(e.repeat),this.center.copy(e.center),this.rotation=e.rotation,this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrix.copy(e.matrix),this.generateMipmaps=e.generateMipmaps,this.premultiplyAlpha=e.premultiplyAlpha,this.flipY=e.flipY,this.unpackAlignment=e.unpackAlignment,this.colorSpace=e.colorSpace,this.renderTarget=e.renderTarget,this.isRenderTargetTexture=e.isRenderTargetTexture,this.isArrayTexture=e.isArrayTexture,this.userData=JSON.parse(JSON.stringify(e.userData)),this.needsUpdate=!0,this}setValues(e){for(const t in e){const n=e[t];if(n===void 0){console.warn(`THREE.Texture.setValues(): parameter '${t}' has value of undefined.`);continue}const a=this[t];if(a===void 0){console.warn(`THREE.Texture.setValues(): property '${t}' does not exist.`);continue}a&&n&&a.isVector2&&n.isVector2||a&&n&&a.isVector3&&n.isVector3||a&&n&&a.isMatrix3&&n.isMatrix3?a.copy(n):this[t]=n}}toJSON(e){const t=e===void 0||typeof e=="string";if(!t&&e.textures[this.uuid]!==void 0)return e.textures[this.uuid];const n={metadata:{version:4.7,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(e).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(n.userData=this.userData),t||(e.textures[this.uuid]=n),n}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(e){if(this.mapping!==Yl)return e;if(e.applyMatrix3(this.matrix),e.x<0||e.x>1)switch(this.wrapS){case Ja:e.x=e.x-Math.floor(e.x);break;case wi:e.x=e.x<0?0:1;break;case Qa:Math.abs(Math.floor(e.x)%2)===1?e.x=Math.ceil(e.x)-e.x:e.x=e.x-Math.floor(e.x);break}if(e.y<0||e.y>1)switch(this.wrapT){case Ja:e.y=e.y-Math.floor(e.y);break;case wi:e.y=e.y<0?0:1;break;case Qa:Math.abs(Math.floor(e.y)%2)===1?e.y=Math.ceil(e.y)-e.y:e.y=e.y-Math.floor(e.y);break}return this.flipY&&(e.y=1-e.y),e}set needsUpdate(e){e===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(e){e===!0&&this.pmremVersion++}}on.DEFAULT_IMAGE=null;on.DEFAULT_MAPPING=Yl;on.DEFAULT_ANISOTROPY=1;class Ut{constructor(e=0,t=0,n=0,a=1){Ut.prototype.isVector4=!0,this.x=e,this.y=t,this.z=n,this.w=a}get width(){return this.z}set width(e){this.z=e}get height(){return this.w}set height(e){this.w=e}set(e,t,n,a){return this.x=e,this.y=t,this.z=n,this.w=a,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this.w=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setW(e){return this.w=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;case 3:this.w=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this.w=e.w!==void 0?e.w:1,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this.w+=e.w,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this.w+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this.w=e.w+t.w,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this.w+=e.w*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this.w-=e.w,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this.w-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this.w=e.w-t.w,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this.w*=e.w,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this.w*=e,this}applyMatrix4(e){const t=this.x,n=this.y,a=this.z,o=this.w,l=e.elements;return this.x=l[0]*t+l[4]*n+l[8]*a+l[12]*o,this.y=l[1]*t+l[5]*n+l[9]*a+l[13]*o,this.z=l[2]*t+l[6]*n+l[10]*a+l[14]*o,this.w=l[3]*t+l[7]*n+l[11]*a+l[15]*o,this}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this.w/=e.w,this}divideScalar(e){return this.multiplyScalar(1/e)}setAxisAngleFromQuaternion(e){this.w=2*Math.acos(e.w);const t=Math.sqrt(1-e.w*e.w);return t<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=e.x/t,this.y=e.y/t,this.z=e.z/t),this}setAxisAngleFromRotationMatrix(e){let t,n,a,o;const p=e.elements,f=p[0],_=p[4],v=p[8],x=p[1],E=p[5],R=p[9],C=p[2],y=p[6],m=p[10];if(Math.abs(_-x)<.01&&Math.abs(v-C)<.01&&Math.abs(R-y)<.01){if(Math.abs(_+x)<.1&&Math.abs(v+C)<.1&&Math.abs(R+y)<.1&&Math.abs(f+E+m-3)<.1)return this.set(1,0,0,0),this;t=Math.PI;const I=(f+1)/2,L=(E+1)/2,B=(m+1)/2,D=(_+x)/4,H=(v+C)/4,q=(R+y)/4;return I>L&&I>B?I<.01?(n=0,a=.707106781,o=.707106781):(n=Math.sqrt(I),a=D/n,o=H/n):L>B?L<.01?(n=.707106781,a=0,o=.707106781):(a=Math.sqrt(L),n=D/a,o=q/a):B<.01?(n=.707106781,a=.707106781,o=0):(o=Math.sqrt(B),n=H/o,a=q/o),this.set(n,a,o,t),this}let N=Math.sqrt((y-R)*(y-R)+(v-C)*(v-C)+(x-_)*(x-_));return Math.abs(N)<.001&&(N=1),this.x=(y-R)/N,this.y=(v-C)/N,this.z=(x-_)/N,this.w=Math.acos((f+E+m-1)/2),this}setFromMatrixPosition(e){const t=e.elements;return this.x=t[12],this.y=t[13],this.z=t[14],this.w=t[15],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this.w=Math.min(this.w,e.w),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this.w=Math.max(this.w,e.w),this}clamp(e,t){return this.x=lt(this.x,e.x,t.x),this.y=lt(this.y,e.y,t.y),this.z=lt(this.z,e.z,t.z),this.w=lt(this.w,e.w,t.w),this}clampScalar(e,t){return this.x=lt(this.x,e,t),this.y=lt(this.y,e,t),this.z=lt(this.z,e,t),this.w=lt(this.w,e,t),this}clampLength(e,t){const n=this.length();return this.divideScalar(n||1).multiplyScalar(lt(n,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z+this.w*e.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this.w+=(e.w-this.w)*t,this}lerpVectors(e,t,n){return this.x=e.x+(t.x-e.x)*n,this.y=e.y+(t.y-e.y)*n,this.z=e.z+(t.z-e.z)*n,this.w=e.w+(t.w-e.w)*n,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z&&e.w===this.w}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this.w=e[t+3],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e[t+3]=this.w,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this.w=e.getW(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}}class L_ extends Li{constructor(e=1,t=1,n={}){super(),n=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:Pn,depthBuffer:!0,stencilBuffer:!1,resolveDepthBuffer:!0,resolveStencilBuffer:!0,depthTexture:null,samples:0,count:1,depth:1,multiview:!1},n),this.isRenderTarget=!0,this.width=e,this.height=t,this.depth=n.depth,this.scissor=new Ut(0,0,e,t),this.scissorTest=!1,this.viewport=new Ut(0,0,e,t);const a={width:e,height:t,depth:n.depth},o=new on(a);this.textures=[];const l=n.count;for(let u=0;u<l;u++)this.textures[u]=o.clone(),this.textures[u].isRenderTargetTexture=!0,this.textures[u].renderTarget=this;this._setTextureOptions(n),this.depthBuffer=n.depthBuffer,this.stencilBuffer=n.stencilBuffer,this.resolveDepthBuffer=n.resolveDepthBuffer,this.resolveStencilBuffer=n.resolveStencilBuffer,this._depthTexture=null,this.depthTexture=n.depthTexture,this.samples=n.samples,this.multiview=n.multiview}_setTextureOptions(e={}){const t={minFilter:Pn,generateMipmaps:!1,flipY:!1,internalFormat:null};e.mapping!==void 0&&(t.mapping=e.mapping),e.wrapS!==void 0&&(t.wrapS=e.wrapS),e.wrapT!==void 0&&(t.wrapT=e.wrapT),e.wrapR!==void 0&&(t.wrapR=e.wrapR),e.magFilter!==void 0&&(t.magFilter=e.magFilter),e.minFilter!==void 0&&(t.minFilter=e.minFilter),e.format!==void 0&&(t.format=e.format),e.type!==void 0&&(t.type=e.type),e.anisotropy!==void 0&&(t.anisotropy=e.anisotropy),e.colorSpace!==void 0&&(t.colorSpace=e.colorSpace),e.flipY!==void 0&&(t.flipY=e.flipY),e.generateMipmaps!==void 0&&(t.generateMipmaps=e.generateMipmaps),e.internalFormat!==void 0&&(t.internalFormat=e.internalFormat);for(let n=0;n<this.textures.length;n++)this.textures[n].setValues(t)}get texture(){return this.textures[0]}set texture(e){this.textures[0]=e}set depthTexture(e){this._depthTexture!==null&&(this._depthTexture.renderTarget=null),e!==null&&(e.renderTarget=this),this._depthTexture=e}get depthTexture(){return this._depthTexture}setSize(e,t,n=1){if(this.width!==e||this.height!==t||this.depth!==n){this.width=e,this.height=t,this.depth=n;for(let a=0,o=this.textures.length;a<o;a++)this.textures[a].image.width=e,this.textures[a].image.height=t,this.textures[a].image.depth=n,this.textures[a].isArrayTexture=this.textures[a].image.depth>1;this.dispose()}this.viewport.set(0,0,e,t),this.scissor.set(0,0,e,t)}clone(){return new this.constructor().copy(this)}copy(e){this.width=e.width,this.height=e.height,this.depth=e.depth,this.scissor.copy(e.scissor),this.scissorTest=e.scissorTest,this.viewport.copy(e.viewport),this.textures.length=0;for(let t=0,n=e.textures.length;t<n;t++){this.textures[t]=e.textures[t].clone(),this.textures[t].isRenderTargetTexture=!0,this.textures[t].renderTarget=this;const a=Object.assign({},e.textures[t].image);this.textures[t].source=new Oo(a)}return this.depthBuffer=e.depthBuffer,this.stencilBuffer=e.stencilBuffer,this.resolveDepthBuffer=e.resolveDepthBuffer,this.resolveStencilBuffer=e.resolveStencilBuffer,e.depthTexture!==null&&(this.depthTexture=e.depthTexture.clone()),this.samples=e.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}}class Pi extends L_{constructor(e=1,t=1,n={}){super(e,t,n),this.isWebGLRenderTarget=!0}}class ou extends on{constructor(e=null,t=1,n=1,a=1){super(null),this.isDataArrayTexture=!0,this.image={data:e,width:t,height:n,depth:a},this.magFilter=Tn,this.minFilter=Tn,this.wrapR=wi,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}addLayerUpdate(e){this.layerUpdates.add(e)}clearLayerUpdates(){this.layerUpdates.clear()}}class I_ extends on{constructor(e=null,t=1,n=1,a=1){super(null),this.isData3DTexture=!0,this.image={data:e,width:t,height:n,depth:a},this.magFilter=Tn,this.minFilter=Tn,this.wrapR=wi,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}class Rr{constructor(e=new X(1/0,1/0,1/0),t=new X(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=e,this.max=t}set(e,t){return this.min.copy(e),this.max.copy(t),this}setFromArray(e){this.makeEmpty();for(let t=0,n=e.length;t<n;t+=3)this.expandByPoint(xn.fromArray(e,t));return this}setFromBufferAttribute(e){this.makeEmpty();for(let t=0,n=e.count;t<n;t++)this.expandByPoint(xn.fromBufferAttribute(e,t));return this}setFromPoints(e){this.makeEmpty();for(let t=0,n=e.length;t<n;t++)this.expandByPoint(e[t]);return this}setFromCenterAndSize(e,t){const n=xn.copy(t).multiplyScalar(.5);return this.min.copy(e).sub(n),this.max.copy(e).add(n),this}setFromObject(e,t=!1){return this.makeEmpty(),this.expandByObject(e,t)}clone(){return new this.constructor().copy(this)}copy(e){return this.min.copy(e.min),this.max.copy(e.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(e){return this.isEmpty()?e.set(0,0,0):e.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(e){return this.isEmpty()?e.set(0,0,0):e.subVectors(this.max,this.min)}expandByPoint(e){return this.min.min(e),this.max.max(e),this}expandByVector(e){return this.min.sub(e),this.max.add(e),this}expandByScalar(e){return this.min.addScalar(-e),this.max.addScalar(e),this}expandByObject(e,t=!1){e.updateWorldMatrix(!1,!1);const n=e.geometry;if(n!==void 0){const o=n.getAttribute("position");if(t===!0&&o!==void 0&&e.isInstancedMesh!==!0)for(let l=0,u=o.count;l<u;l++)e.isMesh===!0?e.getVertexPosition(l,xn):xn.fromBufferAttribute(o,l),xn.applyMatrix4(e.matrixWorld),this.expandByPoint(xn);else e.boundingBox!==void 0?(e.boundingBox===null&&e.computeBoundingBox(),Zr.copy(e.boundingBox)):(n.boundingBox===null&&n.computeBoundingBox(),Zr.copy(n.boundingBox)),Zr.applyMatrix4(e.matrixWorld),this.union(Zr)}const a=e.children;for(let o=0,l=a.length;o<l;o++)this.expandByObject(a[o],t);return this}containsPoint(e){return e.x>=this.min.x&&e.x<=this.max.x&&e.y>=this.min.y&&e.y<=this.max.y&&e.z>=this.min.z&&e.z<=this.max.z}containsBox(e){return this.min.x<=e.min.x&&e.max.x<=this.max.x&&this.min.y<=e.min.y&&e.max.y<=this.max.y&&this.min.z<=e.min.z&&e.max.z<=this.max.z}getParameter(e,t){return t.set((e.x-this.min.x)/(this.max.x-this.min.x),(e.y-this.min.y)/(this.max.y-this.min.y),(e.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(e){return e.max.x>=this.min.x&&e.min.x<=this.max.x&&e.max.y>=this.min.y&&e.min.y<=this.max.y&&e.max.z>=this.min.z&&e.min.z<=this.max.z}intersectsSphere(e){return this.clampPoint(e.center,xn),xn.distanceToSquared(e.center)<=e.radius*e.radius}intersectsPlane(e){let t,n;return e.normal.x>0?(t=e.normal.x*this.min.x,n=e.normal.x*this.max.x):(t=e.normal.x*this.max.x,n=e.normal.x*this.min.x),e.normal.y>0?(t+=e.normal.y*this.min.y,n+=e.normal.y*this.max.y):(t+=e.normal.y*this.max.y,n+=e.normal.y*this.min.y),e.normal.z>0?(t+=e.normal.z*this.min.z,n+=e.normal.z*this.max.z):(t+=e.normal.z*this.max.z,n+=e.normal.z*this.min.z),t<=-e.constant&&n>=-e.constant}intersectsTriangle(e){if(this.isEmpty())return!1;this.getCenter(pr),Jr.subVectors(this.max,pr),Ni.subVectors(e.a,pr),Oi.subVectors(e.b,pr),ki.subVectors(e.c,pr),Yn.subVectors(Oi,Ni),Kn.subVectors(ki,Oi),gi.subVectors(Ni,ki);let t=[0,-Yn.z,Yn.y,0,-Kn.z,Kn.y,0,-gi.z,gi.y,Yn.z,0,-Yn.x,Kn.z,0,-Kn.x,gi.z,0,-gi.x,-Yn.y,Yn.x,0,-Kn.y,Kn.x,0,-gi.y,gi.x,0];return!ua(t,Ni,Oi,ki,Jr)||(t=[1,0,0,0,1,0,0,0,1],!ua(t,Ni,Oi,ki,Jr))?!1:(Qr.crossVectors(Yn,Kn),t=[Qr.x,Qr.y,Qr.z],ua(t,Ni,Oi,ki,Jr))}clampPoint(e,t){return t.copy(e).clamp(this.min,this.max)}distanceToPoint(e){return this.clampPoint(e,xn).distanceTo(e)}getBoundingSphere(e){return this.isEmpty()?e.makeEmpty():(this.getCenter(e.center),e.radius=this.getSize(xn).length()*.5),e}intersect(e){return this.min.max(e.min),this.max.min(e.max),this.isEmpty()&&this.makeEmpty(),this}union(e){return this.min.min(e.min),this.max.max(e.max),this}applyMatrix4(e){return this.isEmpty()?this:(Bn[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(e),Bn[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(e),Bn[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(e),Bn[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(e),Bn[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(e),Bn[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(e),Bn[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(e),Bn[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(e),this.setFromPoints(Bn),this)}translate(e){return this.min.add(e),this.max.add(e),this}equals(e){return e.min.equals(this.min)&&e.max.equals(this.max)}toJSON(){return{min:this.min.toArray(),max:this.max.toArray()}}fromJSON(e){return this.min.fromArray(e.min),this.max.fromArray(e.max),this}}const Bn=[new X,new X,new X,new X,new X,new X,new X,new X],xn=new X,Zr=new Rr,Ni=new X,Oi=new X,ki=new X,Yn=new X,Kn=new X,gi=new X,pr=new X,Jr=new X,Qr=new X,vi=new X;function ua(r,e,t,n,a){for(let o=0,l=r.length-3;o<=l;o+=3){vi.fromArray(r,o);const u=a.x*Math.abs(vi.x)+a.y*Math.abs(vi.y)+a.z*Math.abs(vi.z),p=e.dot(vi),f=t.dot(vi),_=n.dot(vi);if(Math.max(-Math.max(p,f,_),Math.min(p,f,_))>u)return!1}return!0}const F_=new Rr,mr=new X,ha=new X;class Us{constructor(e=new X,t=-1){this.isSphere=!0,this.center=e,this.radius=t}set(e,t){return this.center.copy(e),this.radius=t,this}setFromPoints(e,t){const n=this.center;t!==void 0?n.copy(t):F_.setFromPoints(e).getCenter(n);let a=0;for(let o=0,l=e.length;o<l;o++)a=Math.max(a,n.distanceToSquared(e[o]));return this.radius=Math.sqrt(a),this}copy(e){return this.center.copy(e.center),this.radius=e.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(e){return e.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(e){return e.distanceTo(this.center)-this.radius}intersectsSphere(e){const t=this.radius+e.radius;return e.center.distanceToSquared(this.center)<=t*t}intersectsBox(e){return e.intersectsSphere(this)}intersectsPlane(e){return Math.abs(e.distanceToPoint(this.center))<=this.radius}clampPoint(e,t){const n=this.center.distanceToSquared(e);return t.copy(e),n>this.radius*this.radius&&(t.sub(this.center).normalize(),t.multiplyScalar(this.radius).add(this.center)),t}getBoundingBox(e){return this.isEmpty()?(e.makeEmpty(),e):(e.set(this.center,this.center),e.expandByScalar(this.radius),e)}applyMatrix4(e){return this.center.applyMatrix4(e),this.radius=this.radius*e.getMaxScaleOnAxis(),this}translate(e){return this.center.add(e),this}expandByPoint(e){if(this.isEmpty())return this.center.copy(e),this.radius=0,this;mr.subVectors(e,this.center);const t=mr.lengthSq();if(t>this.radius*this.radius){const n=Math.sqrt(t),a=(n-this.radius)*.5;this.center.addScaledVector(mr,a/n),this.radius+=a}return this}union(e){return e.isEmpty()?this:this.isEmpty()?(this.copy(e),this):(this.center.equals(e.center)===!0?this.radius=Math.max(this.radius,e.radius):(ha.subVectors(e.center,this.center).setLength(e.radius),this.expandByPoint(mr.copy(e.center).add(ha)),this.expandByPoint(mr.copy(e.center).sub(ha))),this)}equals(e){return e.center.equals(this.center)&&e.radius===this.radius}clone(){return new this.constructor().copy(this)}toJSON(){return{radius:this.radius,center:this.center.toArray()}}fromJSON(e){return this.radius=e.radius,this.center.fromArray(e.center),this}}const zn=new X,da=new X,es=new X,Zn=new X,fa=new X,ts=new X,pa=new X;class Ns{constructor(e=new X,t=new X(0,0,-1)){this.origin=e,this.direction=t}set(e,t){return this.origin.copy(e),this.direction.copy(t),this}copy(e){return this.origin.copy(e.origin),this.direction.copy(e.direction),this}at(e,t){return t.copy(this.origin).addScaledVector(this.direction,e)}lookAt(e){return this.direction.copy(e).sub(this.origin).normalize(),this}recast(e){return this.origin.copy(this.at(e,zn)),this}closestPointToPoint(e,t){t.subVectors(e,this.origin);const n=t.dot(this.direction);return n<0?t.copy(this.origin):t.copy(this.origin).addScaledVector(this.direction,n)}distanceToPoint(e){return Math.sqrt(this.distanceSqToPoint(e))}distanceSqToPoint(e){const t=zn.subVectors(e,this.origin).dot(this.direction);return t<0?this.origin.distanceToSquared(e):(zn.copy(this.origin).addScaledVector(this.direction,t),zn.distanceToSquared(e))}distanceSqToSegment(e,t,n,a){da.copy(e).add(t).multiplyScalar(.5),es.copy(t).sub(e).normalize(),Zn.copy(this.origin).sub(da);const o=e.distanceTo(t)*.5,l=-this.direction.dot(es),u=Zn.dot(this.direction),p=-Zn.dot(es),f=Zn.lengthSq(),_=Math.abs(1-l*l);let v,x,E,R;if(_>0)if(v=l*p-u,x=l*u-p,R=o*_,v>=0)if(x>=-R)if(x<=R){const C=1/_;v*=C,x*=C,E=v*(v+l*x+2*u)+x*(l*v+x+2*p)+f}else x=o,v=Math.max(0,-(l*x+u)),E=-v*v+x*(x+2*p)+f;else x=-o,v=Math.max(0,-(l*x+u)),E=-v*v+x*(x+2*p)+f;else x<=-R?(v=Math.max(0,-(-l*o+u)),x=v>0?-o:Math.min(Math.max(-o,-p),o),E=-v*v+x*(x+2*p)+f):x<=R?(v=0,x=Math.min(Math.max(-o,-p),o),E=x*(x+2*p)+f):(v=Math.max(0,-(l*o+u)),x=v>0?o:Math.min(Math.max(-o,-p),o),E=-v*v+x*(x+2*p)+f);else x=l>0?-o:o,v=Math.max(0,-(l*x+u)),E=-v*v+x*(x+2*p)+f;return n&&n.copy(this.origin).addScaledVector(this.direction,v),a&&a.copy(da).addScaledVector(es,x),E}intersectSphere(e,t){zn.subVectors(e.center,this.origin);const n=zn.dot(this.direction),a=zn.dot(zn)-n*n,o=e.radius*e.radius;if(a>o)return null;const l=Math.sqrt(o-a),u=n-l,p=n+l;return p<0?null:u<0?this.at(p,t):this.at(u,t)}intersectsSphere(e){return e.radius<0?!1:this.distanceSqToPoint(e.center)<=e.radius*e.radius}distanceToPlane(e){const t=e.normal.dot(this.direction);if(t===0)return e.distanceToPoint(this.origin)===0?0:null;const n=-(this.origin.dot(e.normal)+e.constant)/t;return n>=0?n:null}intersectPlane(e,t){const n=this.distanceToPlane(e);return n===null?null:this.at(n,t)}intersectsPlane(e){const t=e.distanceToPoint(this.origin);return t===0||e.normal.dot(this.direction)*t<0}intersectBox(e,t){let n,a,o,l,u,p;const f=1/this.direction.x,_=1/this.direction.y,v=1/this.direction.z,x=this.origin;return f>=0?(n=(e.min.x-x.x)*f,a=(e.max.x-x.x)*f):(n=(e.max.x-x.x)*f,a=(e.min.x-x.x)*f),_>=0?(o=(e.min.y-x.y)*_,l=(e.max.y-x.y)*_):(o=(e.max.y-x.y)*_,l=(e.min.y-x.y)*_),n>l||o>a||((o>n||isNaN(n))&&(n=o),(l<a||isNaN(a))&&(a=l),v>=0?(u=(e.min.z-x.z)*v,p=(e.max.z-x.z)*v):(u=(e.max.z-x.z)*v,p=(e.min.z-x.z)*v),n>p||u>a)||((u>n||n!==n)&&(n=u),(p<a||a!==a)&&(a=p),a<0)?null:this.at(n>=0?n:a,t)}intersectsBox(e){return this.intersectBox(e,zn)!==null}intersectTriangle(e,t,n,a,o){fa.subVectors(t,e),ts.subVectors(n,e),pa.crossVectors(fa,ts);let l=this.direction.dot(pa),u;if(l>0){if(a)return null;u=1}else if(l<0)u=-1,l=-l;else return null;Zn.subVectors(this.origin,e);const p=u*this.direction.dot(ts.crossVectors(Zn,ts));if(p<0)return null;const f=u*this.direction.dot(fa.cross(Zn));if(f<0||p+f>l)return null;const _=-u*Zn.dot(pa);return _<0?null:this.at(_/l,o)}applyMatrix4(e){return this.origin.applyMatrix4(e),this.direction.transformDirection(e),this}equals(e){return e.origin.equals(this.origin)&&e.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}}class Ft{constructor(e,t,n,a,o,l,u,p,f,_,v,x,E,R,C,y){Ft.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],e!==void 0&&this.set(e,t,n,a,o,l,u,p,f,_,v,x,E,R,C,y)}set(e,t,n,a,o,l,u,p,f,_,v,x,E,R,C,y){const m=this.elements;return m[0]=e,m[4]=t,m[8]=n,m[12]=a,m[1]=o,m[5]=l,m[9]=u,m[13]=p,m[2]=f,m[6]=_,m[10]=v,m[14]=x,m[3]=E,m[7]=R,m[11]=C,m[15]=y,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new Ft().fromArray(this.elements)}copy(e){const t=this.elements,n=e.elements;return t[0]=n[0],t[1]=n[1],t[2]=n[2],t[3]=n[3],t[4]=n[4],t[5]=n[5],t[6]=n[6],t[7]=n[7],t[8]=n[8],t[9]=n[9],t[10]=n[10],t[11]=n[11],t[12]=n[12],t[13]=n[13],t[14]=n[14],t[15]=n[15],this}copyPosition(e){const t=this.elements,n=e.elements;return t[12]=n[12],t[13]=n[13],t[14]=n[14],this}setFromMatrix3(e){const t=e.elements;return this.set(t[0],t[3],t[6],0,t[1],t[4],t[7],0,t[2],t[5],t[8],0,0,0,0,1),this}extractBasis(e,t,n){return e.setFromMatrixColumn(this,0),t.setFromMatrixColumn(this,1),n.setFromMatrixColumn(this,2),this}makeBasis(e,t,n){return this.set(e.x,t.x,n.x,0,e.y,t.y,n.y,0,e.z,t.z,n.z,0,0,0,0,1),this}extractRotation(e){const t=this.elements,n=e.elements,a=1/Bi.setFromMatrixColumn(e,0).length(),o=1/Bi.setFromMatrixColumn(e,1).length(),l=1/Bi.setFromMatrixColumn(e,2).length();return t[0]=n[0]*a,t[1]=n[1]*a,t[2]=n[2]*a,t[3]=0,t[4]=n[4]*o,t[5]=n[5]*o,t[6]=n[6]*o,t[7]=0,t[8]=n[8]*l,t[9]=n[9]*l,t[10]=n[10]*l,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromEuler(e){const t=this.elements,n=e.x,a=e.y,o=e.z,l=Math.cos(n),u=Math.sin(n),p=Math.cos(a),f=Math.sin(a),_=Math.cos(o),v=Math.sin(o);if(e.order==="XYZ"){const x=l*_,E=l*v,R=u*_,C=u*v;t[0]=p*_,t[4]=-p*v,t[8]=f,t[1]=E+R*f,t[5]=x-C*f,t[9]=-u*p,t[2]=C-x*f,t[6]=R+E*f,t[10]=l*p}else if(e.order==="YXZ"){const x=p*_,E=p*v,R=f*_,C=f*v;t[0]=x+C*u,t[4]=R*u-E,t[8]=l*f,t[1]=l*v,t[5]=l*_,t[9]=-u,t[2]=E*u-R,t[6]=C+x*u,t[10]=l*p}else if(e.order==="ZXY"){const x=p*_,E=p*v,R=f*_,C=f*v;t[0]=x-C*u,t[4]=-l*v,t[8]=R+E*u,t[1]=E+R*u,t[5]=l*_,t[9]=C-x*u,t[2]=-l*f,t[6]=u,t[10]=l*p}else if(e.order==="ZYX"){const x=l*_,E=l*v,R=u*_,C=u*v;t[0]=p*_,t[4]=R*f-E,t[8]=x*f+C,t[1]=p*v,t[5]=C*f+x,t[9]=E*f-R,t[2]=-f,t[6]=u*p,t[10]=l*p}else if(e.order==="YZX"){const x=l*p,E=l*f,R=u*p,C=u*f;t[0]=p*_,t[4]=C-x*v,t[8]=R*v+E,t[1]=v,t[5]=l*_,t[9]=-u*_,t[2]=-f*_,t[6]=E*v+R,t[10]=x-C*v}else if(e.order==="XZY"){const x=l*p,E=l*f,R=u*p,C=u*f;t[0]=p*_,t[4]=-v,t[8]=f*_,t[1]=x*v+C,t[5]=l*_,t[9]=E*v-R,t[2]=R*v-E,t[6]=u*_,t[10]=C*v+x}return t[3]=0,t[7]=0,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromQuaternion(e){return this.compose(U_,e,N_)}lookAt(e,t,n){const a=this.elements;return ln.subVectors(e,t),ln.lengthSq()===0&&(ln.z=1),ln.normalize(),Jn.crossVectors(n,ln),Jn.lengthSq()===0&&(Math.abs(n.z)===1?ln.x+=1e-4:ln.z+=1e-4,ln.normalize(),Jn.crossVectors(n,ln)),Jn.normalize(),ns.crossVectors(ln,Jn),a[0]=Jn.x,a[4]=ns.x,a[8]=ln.x,a[1]=Jn.y,a[5]=ns.y,a[9]=ln.y,a[2]=Jn.z,a[6]=ns.z,a[10]=ln.z,this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){const n=e.elements,a=t.elements,o=this.elements,l=n[0],u=n[4],p=n[8],f=n[12],_=n[1],v=n[5],x=n[9],E=n[13],R=n[2],C=n[6],y=n[10],m=n[14],N=n[3],I=n[7],L=n[11],B=n[15],D=a[0],H=a[4],q=a[8],P=a[12],M=a[1],O=a[5],te=a[9],ee=a[13],Z=a[2],he=a[6],ae=a[10],Se=a[14],re=a[3],Ae=a[7],De=a[11],Ve=a[15];return o[0]=l*D+u*M+p*Z+f*re,o[4]=l*H+u*O+p*he+f*Ae,o[8]=l*q+u*te+p*ae+f*De,o[12]=l*P+u*ee+p*Se+f*Ve,o[1]=_*D+v*M+x*Z+E*re,o[5]=_*H+v*O+x*he+E*Ae,o[9]=_*q+v*te+x*ae+E*De,o[13]=_*P+v*ee+x*Se+E*Ve,o[2]=R*D+C*M+y*Z+m*re,o[6]=R*H+C*O+y*he+m*Ae,o[10]=R*q+C*te+y*ae+m*De,o[14]=R*P+C*ee+y*Se+m*Ve,o[3]=N*D+I*M+L*Z+B*re,o[7]=N*H+I*O+L*he+B*Ae,o[11]=N*q+I*te+L*ae+B*De,o[15]=N*P+I*ee+L*Se+B*Ve,this}multiplyScalar(e){const t=this.elements;return t[0]*=e,t[4]*=e,t[8]*=e,t[12]*=e,t[1]*=e,t[5]*=e,t[9]*=e,t[13]*=e,t[2]*=e,t[6]*=e,t[10]*=e,t[14]*=e,t[3]*=e,t[7]*=e,t[11]*=e,t[15]*=e,this}determinant(){const e=this.elements,t=e[0],n=e[4],a=e[8],o=e[12],l=e[1],u=e[5],p=e[9],f=e[13],_=e[2],v=e[6],x=e[10],E=e[14],R=e[3],C=e[7],y=e[11],m=e[15];return R*(+o*p*v-a*f*v-o*u*x+n*f*x+a*u*E-n*p*E)+C*(+t*p*E-t*f*x+o*l*x-a*l*E+a*f*_-o*p*_)+y*(+t*f*v-t*u*E-o*l*v+n*l*E+o*u*_-n*f*_)+m*(-a*u*_-t*p*v+t*u*x+a*l*v-n*l*x+n*p*_)}transpose(){const e=this.elements;let t;return t=e[1],e[1]=e[4],e[4]=t,t=e[2],e[2]=e[8],e[8]=t,t=e[6],e[6]=e[9],e[9]=t,t=e[3],e[3]=e[12],e[12]=t,t=e[7],e[7]=e[13],e[13]=t,t=e[11],e[11]=e[14],e[14]=t,this}setPosition(e,t,n){const a=this.elements;return e.isVector3?(a[12]=e.x,a[13]=e.y,a[14]=e.z):(a[12]=e,a[13]=t,a[14]=n),this}invert(){const e=this.elements,t=e[0],n=e[1],a=e[2],o=e[3],l=e[4],u=e[5],p=e[6],f=e[7],_=e[8],v=e[9],x=e[10],E=e[11],R=e[12],C=e[13],y=e[14],m=e[15],N=v*y*f-C*x*f+C*p*E-u*y*E-v*p*m+u*x*m,I=R*x*f-_*y*f-R*p*E+l*y*E+_*p*m-l*x*m,L=_*C*f-R*v*f+R*u*E-l*C*E-_*u*m+l*v*m,B=R*v*p-_*C*p-R*u*x+l*C*x+_*u*y-l*v*y,D=t*N+n*I+a*L+o*B;if(D===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);const H=1/D;return e[0]=N*H,e[1]=(C*x*o-v*y*o-C*a*E+n*y*E+v*a*m-n*x*m)*H,e[2]=(u*y*o-C*p*o+C*a*f-n*y*f-u*a*m+n*p*m)*H,e[3]=(v*p*o-u*x*o-v*a*f+n*x*f+u*a*E-n*p*E)*H,e[4]=I*H,e[5]=(_*y*o-R*x*o+R*a*E-t*y*E-_*a*m+t*x*m)*H,e[6]=(R*p*o-l*y*o-R*a*f+t*y*f+l*a*m-t*p*m)*H,e[7]=(l*x*o-_*p*o+_*a*f-t*x*f-l*a*E+t*p*E)*H,e[8]=L*H,e[9]=(R*v*o-_*C*o-R*n*E+t*C*E+_*n*m-t*v*m)*H,e[10]=(l*C*o-R*u*o+R*n*f-t*C*f-l*n*m+t*u*m)*H,e[11]=(_*u*o-l*v*o-_*n*f+t*v*f+l*n*E-t*u*E)*H,e[12]=B*H,e[13]=(_*C*a-R*v*a+R*n*x-t*C*x-_*n*y+t*v*y)*H,e[14]=(R*u*a-l*C*a-R*n*p+t*C*p+l*n*y-t*u*y)*H,e[15]=(l*v*a-_*u*a+_*n*p-t*v*p-l*n*x+t*u*x)*H,this}scale(e){const t=this.elements,n=e.x,a=e.y,o=e.z;return t[0]*=n,t[4]*=a,t[8]*=o,t[1]*=n,t[5]*=a,t[9]*=o,t[2]*=n,t[6]*=a,t[10]*=o,t[3]*=n,t[7]*=a,t[11]*=o,this}getMaxScaleOnAxis(){const e=this.elements,t=e[0]*e[0]+e[1]*e[1]+e[2]*e[2],n=e[4]*e[4]+e[5]*e[5]+e[6]*e[6],a=e[8]*e[8]+e[9]*e[9]+e[10]*e[10];return Math.sqrt(Math.max(t,n,a))}makeTranslation(e,t,n){return e.isVector3?this.set(1,0,0,e.x,0,1,0,e.y,0,0,1,e.z,0,0,0,1):this.set(1,0,0,e,0,1,0,t,0,0,1,n,0,0,0,1),this}makeRotationX(e){const t=Math.cos(e),n=Math.sin(e);return this.set(1,0,0,0,0,t,-n,0,0,n,t,0,0,0,0,1),this}makeRotationY(e){const t=Math.cos(e),n=Math.sin(e);return this.set(t,0,n,0,0,1,0,0,-n,0,t,0,0,0,0,1),this}makeRotationZ(e){const t=Math.cos(e),n=Math.sin(e);return this.set(t,-n,0,0,n,t,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(e,t){const n=Math.cos(t),a=Math.sin(t),o=1-n,l=e.x,u=e.y,p=e.z,f=o*l,_=o*u;return this.set(f*l+n,f*u-a*p,f*p+a*u,0,f*u+a*p,_*u+n,_*p-a*l,0,f*p-a*u,_*p+a*l,o*p*p+n,0,0,0,0,1),this}makeScale(e,t,n){return this.set(e,0,0,0,0,t,0,0,0,0,n,0,0,0,0,1),this}makeShear(e,t,n,a,o,l){return this.set(1,n,o,0,e,1,l,0,t,a,1,0,0,0,0,1),this}compose(e,t,n){const a=this.elements,o=t._x,l=t._y,u=t._z,p=t._w,f=o+o,_=l+l,v=u+u,x=o*f,E=o*_,R=o*v,C=l*_,y=l*v,m=u*v,N=p*f,I=p*_,L=p*v,B=n.x,D=n.y,H=n.z;return a[0]=(1-(C+m))*B,a[1]=(E+L)*B,a[2]=(R-I)*B,a[3]=0,a[4]=(E-L)*D,a[5]=(1-(x+m))*D,a[6]=(y+N)*D,a[7]=0,a[8]=(R+I)*H,a[9]=(y-N)*H,a[10]=(1-(x+C))*H,a[11]=0,a[12]=e.x,a[13]=e.y,a[14]=e.z,a[15]=1,this}decompose(e,t,n){const a=this.elements;let o=Bi.set(a[0],a[1],a[2]).length();const l=Bi.set(a[4],a[5],a[6]).length(),u=Bi.set(a[8],a[9],a[10]).length();this.determinant()<0&&(o=-o),e.x=a[12],e.y=a[13],e.z=a[14],yn.copy(this);const f=1/o,_=1/l,v=1/u;return yn.elements[0]*=f,yn.elements[1]*=f,yn.elements[2]*=f,yn.elements[4]*=_,yn.elements[5]*=_,yn.elements[6]*=_,yn.elements[8]*=v,yn.elements[9]*=v,yn.elements[10]*=v,t.setFromRotationMatrix(yn),n.x=o,n.y=l,n.z=u,this}makePerspective(e,t,n,a,o,l,u=Dn,p=!1){const f=this.elements,_=2*o/(t-e),v=2*o/(n-a),x=(t+e)/(t-e),E=(n+a)/(n-a);let R,C;if(p)R=o/(l-o),C=l*o/(l-o);else if(u===Dn)R=-(l+o)/(l-o),C=-2*l*o/(l-o);else if(u===Ps)R=-l/(l-o),C=-l*o/(l-o);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+u);return f[0]=_,f[4]=0,f[8]=x,f[12]=0,f[1]=0,f[5]=v,f[9]=E,f[13]=0,f[2]=0,f[6]=0,f[10]=R,f[14]=C,f[3]=0,f[7]=0,f[11]=-1,f[15]=0,this}makeOrthographic(e,t,n,a,o,l,u=Dn,p=!1){const f=this.elements,_=2/(t-e),v=2/(n-a),x=-(t+e)/(t-e),E=-(n+a)/(n-a);let R,C;if(p)R=1/(l-o),C=l/(l-o);else if(u===Dn)R=-2/(l-o),C=-(l+o)/(l-o);else if(u===Ps)R=-1/(l-o),C=-o/(l-o);else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+u);return f[0]=_,f[4]=0,f[8]=0,f[12]=x,f[1]=0,f[5]=v,f[9]=0,f[13]=E,f[2]=0,f[6]=0,f[10]=R,f[14]=C,f[3]=0,f[7]=0,f[11]=0,f[15]=1,this}equals(e){const t=this.elements,n=e.elements;for(let a=0;a<16;a++)if(t[a]!==n[a])return!1;return!0}fromArray(e,t=0){for(let n=0;n<16;n++)this.elements[n]=e[n+t];return this}toArray(e=[],t=0){const n=this.elements;return e[t]=n[0],e[t+1]=n[1],e[t+2]=n[2],e[t+3]=n[3],e[t+4]=n[4],e[t+5]=n[5],e[t+6]=n[6],e[t+7]=n[7],e[t+8]=n[8],e[t+9]=n[9],e[t+10]=n[10],e[t+11]=n[11],e[t+12]=n[12],e[t+13]=n[13],e[t+14]=n[14],e[t+15]=n[15],e}}const Bi=new X,yn=new Ft,U_=new X(0,0,0),N_=new X(1,1,1),Jn=new X,ns=new X,ln=new X,jc=new Ft,$c=new Ci;class Fn{constructor(e=0,t=0,n=0,a=Fn.DEFAULT_ORDER){this.isEuler=!0,this._x=e,this._y=t,this._z=n,this._order=a}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get order(){return this._order}set order(e){this._order=e,this._onChangeCallback()}set(e,t,n,a=this._order){return this._x=e,this._y=t,this._z=n,this._order=a,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(e){return this._x=e._x,this._y=e._y,this._z=e._z,this._order=e._order,this._onChangeCallback(),this}setFromRotationMatrix(e,t=this._order,n=!0){const a=e.elements,o=a[0],l=a[4],u=a[8],p=a[1],f=a[5],_=a[9],v=a[2],x=a[6],E=a[10];switch(t){case"XYZ":this._y=Math.asin(lt(u,-1,1)),Math.abs(u)<.9999999?(this._x=Math.atan2(-_,E),this._z=Math.atan2(-l,o)):(this._x=Math.atan2(x,f),this._z=0);break;case"YXZ":this._x=Math.asin(-lt(_,-1,1)),Math.abs(_)<.9999999?(this._y=Math.atan2(u,E),this._z=Math.atan2(p,f)):(this._y=Math.atan2(-v,o),this._z=0);break;case"ZXY":this._x=Math.asin(lt(x,-1,1)),Math.abs(x)<.9999999?(this._y=Math.atan2(-v,E),this._z=Math.atan2(-l,f)):(this._y=0,this._z=Math.atan2(p,o));break;case"ZYX":this._y=Math.asin(-lt(v,-1,1)),Math.abs(v)<.9999999?(this._x=Math.atan2(x,E),this._z=Math.atan2(p,o)):(this._x=0,this._z=Math.atan2(-l,f));break;case"YZX":this._z=Math.asin(lt(p,-1,1)),Math.abs(p)<.9999999?(this._x=Math.atan2(-_,f),this._y=Math.atan2(-v,o)):(this._x=0,this._y=Math.atan2(u,E));break;case"XZY":this._z=Math.asin(-lt(l,-1,1)),Math.abs(l)<.9999999?(this._x=Math.atan2(x,f),this._y=Math.atan2(u,o)):(this._x=Math.atan2(-_,E),this._y=0);break;default:console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: "+t)}return this._order=t,n===!0&&this._onChangeCallback(),this}setFromQuaternion(e,t,n){return jc.makeRotationFromQuaternion(e),this.setFromRotationMatrix(jc,t,n)}setFromVector3(e,t=this._order){return this.set(e.x,e.y,e.z,t)}reorder(e){return $c.setFromEuler(this),this.setFromQuaternion($c,e)}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._order===this._order}fromArray(e){return this._x=e[0],this._y=e[1],this._z=e[2],e[3]!==void 0&&(this._order=e[3]),this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._order,e}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}}Fn.DEFAULT_ORDER="XYZ";class ko{constructor(){this.mask=1}set(e){this.mask=(1<<e|0)>>>0}enable(e){this.mask|=1<<e|0}enableAll(){this.mask=-1}toggle(e){this.mask^=1<<e|0}disable(e){this.mask&=~(1<<e|0)}disableAll(){this.mask=0}test(e){return(this.mask&e.mask)!==0}isEnabled(e){return(this.mask&(1<<e|0))!==0}}let O_=0;const qc=new X,zi=new Ci,Hn=new Ft,is=new X,_r=new X,k_=new X,B_=new Ci,Yc=new X(1,0,0),Kc=new X(0,1,0),Zc=new X(0,0,1),Jc={type:"added"},z_={type:"removed"},Hi={type:"childadded",child:null},ma={type:"childremoved",child:null};class Wt extends Li{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:O_++}),this.uuid=Ar(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=Wt.DEFAULT_UP.clone();const e=new X,t=new Fn,n=new Ci,a=new X(1,1,1);function o(){n.setFromEuler(t,!1)}function l(){t.setFromQuaternion(n,void 0,!1)}t._onChange(o),n._onChange(l),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:e},rotation:{configurable:!0,enumerable:!0,value:t},quaternion:{configurable:!0,enumerable:!0,value:n},scale:{configurable:!0,enumerable:!0,value:a},modelViewMatrix:{value:new Ft},normalMatrix:{value:new it}}),this.matrix=new Ft,this.matrixWorld=new Ft,this.matrixAutoUpdate=Wt.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=Wt.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new ko,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.customDepthMaterial=void 0,this.customDistanceMaterial=void 0,this.userData={}}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(e){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(e),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(e){return this.quaternion.premultiply(e),this}setRotationFromAxisAngle(e,t){this.quaternion.setFromAxisAngle(e,t)}setRotationFromEuler(e){this.quaternion.setFromEuler(e,!0)}setRotationFromMatrix(e){this.quaternion.setFromRotationMatrix(e)}setRotationFromQuaternion(e){this.quaternion.copy(e)}rotateOnAxis(e,t){return zi.setFromAxisAngle(e,t),this.quaternion.multiply(zi),this}rotateOnWorldAxis(e,t){return zi.setFromAxisAngle(e,t),this.quaternion.premultiply(zi),this}rotateX(e){return this.rotateOnAxis(Yc,e)}rotateY(e){return this.rotateOnAxis(Kc,e)}rotateZ(e){return this.rotateOnAxis(Zc,e)}translateOnAxis(e,t){return qc.copy(e).applyQuaternion(this.quaternion),this.position.add(qc.multiplyScalar(t)),this}translateX(e){return this.translateOnAxis(Yc,e)}translateY(e){return this.translateOnAxis(Kc,e)}translateZ(e){return this.translateOnAxis(Zc,e)}localToWorld(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(this.matrixWorld)}worldToLocal(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(Hn.copy(this.matrixWorld).invert())}lookAt(e,t,n){e.isVector3?is.copy(e):is.set(e,t,n);const a=this.parent;this.updateWorldMatrix(!0,!1),_r.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?Hn.lookAt(_r,is,this.up):Hn.lookAt(is,_r,this.up),this.quaternion.setFromRotationMatrix(Hn),a&&(Hn.extractRotation(a.matrixWorld),zi.setFromRotationMatrix(Hn),this.quaternion.premultiply(zi.invert()))}add(e){if(arguments.length>1){for(let t=0;t<arguments.length;t++)this.add(arguments[t]);return this}return e===this?(console.error("THREE.Object3D.add: object can't be added as a child of itself.",e),this):(e&&e.isObject3D?(e.removeFromParent(),e.parent=this,this.children.push(e),e.dispatchEvent(Jc),Hi.child=e,this.dispatchEvent(Hi),Hi.child=null):console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.",e),this)}remove(e){if(arguments.length>1){for(let n=0;n<arguments.length;n++)this.remove(arguments[n]);return this}const t=this.children.indexOf(e);return t!==-1&&(e.parent=null,this.children.splice(t,1),e.dispatchEvent(z_),ma.child=e,this.dispatchEvent(ma),ma.child=null),this}removeFromParent(){const e=this.parent;return e!==null&&e.remove(this),this}clear(){return this.remove(...this.children)}attach(e){return this.updateWorldMatrix(!0,!1),Hn.copy(this.matrixWorld).invert(),e.parent!==null&&(e.parent.updateWorldMatrix(!0,!1),Hn.multiply(e.parent.matrixWorld)),e.applyMatrix4(Hn),e.removeFromParent(),e.parent=this,this.children.push(e),e.updateWorldMatrix(!1,!0),e.dispatchEvent(Jc),Hi.child=e,this.dispatchEvent(Hi),Hi.child=null,this}getObjectById(e){return this.getObjectByProperty("id",e)}getObjectByName(e){return this.getObjectByProperty("name",e)}getObjectByProperty(e,t){if(this[e]===t)return this;for(let n=0,a=this.children.length;n<a;n++){const l=this.children[n].getObjectByProperty(e,t);if(l!==void 0)return l}}getObjectsByProperty(e,t,n=[]){this[e]===t&&n.push(this);const a=this.children;for(let o=0,l=a.length;o<l;o++)a[o].getObjectsByProperty(e,t,n);return n}getWorldPosition(e){return this.updateWorldMatrix(!0,!1),e.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(_r,e,k_),e}getWorldScale(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(_r,B_,e),e}getWorldDirection(e){this.updateWorldMatrix(!0,!1);const t=this.matrixWorld.elements;return e.set(t[8],t[9],t[10]).normalize()}raycast(){}traverse(e){e(this);const t=this.children;for(let n=0,a=t.length;n<a;n++)t[n].traverse(e)}traverseVisible(e){if(this.visible===!1)return;e(this);const t=this.children;for(let n=0,a=t.length;n<a;n++)t[n].traverseVisible(e)}traverseAncestors(e){const t=this.parent;t!==null&&(e(t),t.traverseAncestors(e))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale),this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(e){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||e)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,e=!0);const t=this.children;for(let n=0,a=t.length;n<a;n++)t[n].updateMatrixWorld(e)}updateWorldMatrix(e,t){const n=this.parent;if(e===!0&&n!==null&&n.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),t===!0){const a=this.children;for(let o=0,l=a.length;o<l;o++)a[o].updateWorldMatrix(!1,!0)}}toJSON(e){const t=e===void 0||typeof e=="string",n={};t&&(e={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},n.metadata={version:4.7,type:"Object",generator:"Object3D.toJSON"});const a={};a.uuid=this.uuid,a.type=this.type,this.name!==""&&(a.name=this.name),this.castShadow===!0&&(a.castShadow=!0),this.receiveShadow===!0&&(a.receiveShadow=!0),this.visible===!1&&(a.visible=!1),this.frustumCulled===!1&&(a.frustumCulled=!1),this.renderOrder!==0&&(a.renderOrder=this.renderOrder),Object.keys(this.userData).length>0&&(a.userData=this.userData),a.layers=this.layers.mask,a.matrix=this.matrix.toArray(),a.up=this.up.toArray(),this.matrixAutoUpdate===!1&&(a.matrixAutoUpdate=!1),this.isInstancedMesh&&(a.type="InstancedMesh",a.count=this.count,a.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(a.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(a.type="BatchedMesh",a.perObjectFrustumCulled=this.perObjectFrustumCulled,a.sortObjects=this.sortObjects,a.drawRanges=this._drawRanges,a.reservedRanges=this._reservedRanges,a.geometryInfo=this._geometryInfo.map(u=>({...u,boundingBox:u.boundingBox?u.boundingBox.toJSON():void 0,boundingSphere:u.boundingSphere?u.boundingSphere.toJSON():void 0})),a.instanceInfo=this._instanceInfo.map(u=>({...u})),a.availableInstanceIds=this._availableInstanceIds.slice(),a.availableGeometryIds=this._availableGeometryIds.slice(),a.nextIndexStart=this._nextIndexStart,a.nextVertexStart=this._nextVertexStart,a.geometryCount=this._geometryCount,a.maxInstanceCount=this._maxInstanceCount,a.maxVertexCount=this._maxVertexCount,a.maxIndexCount=this._maxIndexCount,a.geometryInitialized=this._geometryInitialized,a.matricesTexture=this._matricesTexture.toJSON(e),a.indirectTexture=this._indirectTexture.toJSON(e),this._colorsTexture!==null&&(a.colorsTexture=this._colorsTexture.toJSON(e)),this.boundingSphere!==null&&(a.boundingSphere=this.boundingSphere.toJSON()),this.boundingBox!==null&&(a.boundingBox=this.boundingBox.toJSON()));function o(u,p){return u[p.uuid]===void 0&&(u[p.uuid]=p.toJSON(e)),p.uuid}if(this.isScene)this.background&&(this.background.isColor?a.background=this.background.toJSON():this.background.isTexture&&(a.background=this.background.toJSON(e).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(a.environment=this.environment.toJSON(e).uuid);else if(this.isMesh||this.isLine||this.isPoints){a.geometry=o(e.geometries,this.geometry);const u=this.geometry.parameters;if(u!==void 0&&u.shapes!==void 0){const p=u.shapes;if(Array.isArray(p))for(let f=0,_=p.length;f<_;f++){const v=p[f];o(e.shapes,v)}else o(e.shapes,p)}}if(this.isSkinnedMesh&&(a.bindMode=this.bindMode,a.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(o(e.skeletons,this.skeleton),a.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){const u=[];for(let p=0,f=this.material.length;p<f;p++)u.push(o(e.materials,this.material[p]));a.material=u}else a.material=o(e.materials,this.material);if(this.children.length>0){a.children=[];for(let u=0;u<this.children.length;u++)a.children.push(this.children[u].toJSON(e).object)}if(this.animations.length>0){a.animations=[];for(let u=0;u<this.animations.length;u++){const p=this.animations[u];a.animations.push(o(e.animations,p))}}if(t){const u=l(e.geometries),p=l(e.materials),f=l(e.textures),_=l(e.images),v=l(e.shapes),x=l(e.skeletons),E=l(e.animations),R=l(e.nodes);u.length>0&&(n.geometries=u),p.length>0&&(n.materials=p),f.length>0&&(n.textures=f),_.length>0&&(n.images=_),v.length>0&&(n.shapes=v),x.length>0&&(n.skeletons=x),E.length>0&&(n.animations=E),R.length>0&&(n.nodes=R)}return n.object=a,n;function l(u){const p=[];for(const f in u){const _=u[f];delete _.metadata,p.push(_)}return p}}clone(e){return new this.constructor().copy(this,e)}copy(e,t=!0){if(this.name=e.name,this.up.copy(e.up),this.position.copy(e.position),this.rotation.order=e.rotation.order,this.quaternion.copy(e.quaternion),this.scale.copy(e.scale),this.matrix.copy(e.matrix),this.matrixWorld.copy(e.matrixWorld),this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrixWorldAutoUpdate=e.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=e.matrixWorldNeedsUpdate,this.layers.mask=e.layers.mask,this.visible=e.visible,this.castShadow=e.castShadow,this.receiveShadow=e.receiveShadow,this.frustumCulled=e.frustumCulled,this.renderOrder=e.renderOrder,this.animations=e.animations.slice(),this.userData=JSON.parse(JSON.stringify(e.userData)),t===!0)for(let n=0;n<e.children.length;n++){const a=e.children[n];this.add(a.clone())}return this}}Wt.DEFAULT_UP=new X(0,1,0);Wt.DEFAULT_MATRIX_AUTO_UPDATE=!0;Wt.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;const En=new X,Vn=new X,_a=new X,Gn=new X,Vi=new X,Gi=new X,Qc=new X,ga=new X,va=new X,xa=new X,ya=new Ut,Ea=new Ut,Sa=new Ut;class Sn{constructor(e=new X,t=new X,n=new X){this.a=e,this.b=t,this.c=n}static getNormal(e,t,n,a){a.subVectors(n,t),En.subVectors(e,t),a.cross(En);const o=a.lengthSq();return o>0?a.multiplyScalar(1/Math.sqrt(o)):a.set(0,0,0)}static getBarycoord(e,t,n,a,o){En.subVectors(a,t),Vn.subVectors(n,t),_a.subVectors(e,t);const l=En.dot(En),u=En.dot(Vn),p=En.dot(_a),f=Vn.dot(Vn),_=Vn.dot(_a),v=l*f-u*u;if(v===0)return o.set(0,0,0),null;const x=1/v,E=(f*p-u*_)*x,R=(l*_-u*p)*x;return o.set(1-E-R,R,E)}static containsPoint(e,t,n,a){return this.getBarycoord(e,t,n,a,Gn)===null?!1:Gn.x>=0&&Gn.y>=0&&Gn.x+Gn.y<=1}static getInterpolation(e,t,n,a,o,l,u,p){return this.getBarycoord(e,t,n,a,Gn)===null?(p.x=0,p.y=0,"z"in p&&(p.z=0),"w"in p&&(p.w=0),null):(p.setScalar(0),p.addScaledVector(o,Gn.x),p.addScaledVector(l,Gn.y),p.addScaledVector(u,Gn.z),p)}static getInterpolatedAttribute(e,t,n,a,o,l){return ya.setScalar(0),Ea.setScalar(0),Sa.setScalar(0),ya.fromBufferAttribute(e,t),Ea.fromBufferAttribute(e,n),Sa.fromBufferAttribute(e,a),l.setScalar(0),l.addScaledVector(ya,o.x),l.addScaledVector(Ea,o.y),l.addScaledVector(Sa,o.z),l}static isFrontFacing(e,t,n,a){return En.subVectors(n,t),Vn.subVectors(e,t),En.cross(Vn).dot(a)<0}set(e,t,n){return this.a.copy(e),this.b.copy(t),this.c.copy(n),this}setFromPointsAndIndices(e,t,n,a){return this.a.copy(e[t]),this.b.copy(e[n]),this.c.copy(e[a]),this}setFromAttributeAndIndices(e,t,n,a){return this.a.fromBufferAttribute(e,t),this.b.fromBufferAttribute(e,n),this.c.fromBufferAttribute(e,a),this}clone(){return new this.constructor().copy(this)}copy(e){return this.a.copy(e.a),this.b.copy(e.b),this.c.copy(e.c),this}getArea(){return En.subVectors(this.c,this.b),Vn.subVectors(this.a,this.b),En.cross(Vn).length()*.5}getMidpoint(e){return e.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(e){return Sn.getNormal(this.a,this.b,this.c,e)}getPlane(e){return e.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(e,t){return Sn.getBarycoord(e,this.a,this.b,this.c,t)}getInterpolation(e,t,n,a,o){return Sn.getInterpolation(e,this.a,this.b,this.c,t,n,a,o)}containsPoint(e){return Sn.containsPoint(e,this.a,this.b,this.c)}isFrontFacing(e){return Sn.isFrontFacing(this.a,this.b,this.c,e)}intersectsBox(e){return e.intersectsTriangle(this)}closestPointToPoint(e,t){const n=this.a,a=this.b,o=this.c;let l,u;Vi.subVectors(a,n),Gi.subVectors(o,n),ga.subVectors(e,n);const p=Vi.dot(ga),f=Gi.dot(ga);if(p<=0&&f<=0)return t.copy(n);va.subVectors(e,a);const _=Vi.dot(va),v=Gi.dot(va);if(_>=0&&v<=_)return t.copy(a);const x=p*v-_*f;if(x<=0&&p>=0&&_<=0)return l=p/(p-_),t.copy(n).addScaledVector(Vi,l);xa.subVectors(e,o);const E=Vi.dot(xa),R=Gi.dot(xa);if(R>=0&&E<=R)return t.copy(o);const C=E*f-p*R;if(C<=0&&f>=0&&R<=0)return u=f/(f-R),t.copy(n).addScaledVector(Gi,u);const y=_*R-E*v;if(y<=0&&v-_>=0&&E-R>=0)return Qc.subVectors(o,a),u=(v-_)/(v-_+(E-R)),t.copy(a).addScaledVector(Qc,u);const m=1/(y+C+x);return l=C*m,u=x*m,t.copy(n).addScaledVector(Vi,l).addScaledVector(Gi,u)}equals(e){return e.a.equals(this.a)&&e.b.equals(this.b)&&e.c.equals(this.c)}}const cu={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},Qn={h:0,s:0,l:0},rs={h:0,s:0,l:0};function Ma(r,e,t){return t<0&&(t+=1),t>1&&(t-=1),t<1/6?r+(e-r)*6*t:t<1/2?e:t<2/3?r+(e-r)*6*(2/3-t):r}class ot{constructor(e,t,n){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(e,t,n)}set(e,t,n){if(t===void 0&&n===void 0){const a=e;a&&a.isColor?this.copy(a):typeof a=="number"?this.setHex(a):typeof a=="string"&&this.setStyle(a)}else this.setRGB(e,t,n);return this}setScalar(e){return this.r=e,this.g=e,this.b=e,this}setHex(e,t=hn){return e=Math.floor(e),this.r=(e>>16&255)/255,this.g=(e>>8&255)/255,this.b=(e&255)/255,gt.colorSpaceToWorking(this,t),this}setRGB(e,t,n,a=gt.workingColorSpace){return this.r=e,this.g=t,this.b=n,gt.colorSpaceToWorking(this,a),this}setHSL(e,t,n,a=gt.workingColorSpace){if(e=T_(e,1),t=lt(t,0,1),n=lt(n,0,1),t===0)this.r=this.g=this.b=n;else{const o=n<=.5?n*(1+t):n+t-n*t,l=2*n-o;this.r=Ma(l,o,e+1/3),this.g=Ma(l,o,e),this.b=Ma(l,o,e-1/3)}return gt.colorSpaceToWorking(this,a),this}setStyle(e,t=hn){function n(o){o!==void 0&&parseFloat(o)<1&&console.warn("THREE.Color: Alpha component of "+e+" will be ignored.")}let a;if(a=/^(\w+)\(([^\)]*)\)/.exec(e)){let o;const l=a[1],u=a[2];switch(l){case"rgb":case"rgba":if(o=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(u))return n(o[4]),this.setRGB(Math.min(255,parseInt(o[1],10))/255,Math.min(255,parseInt(o[2],10))/255,Math.min(255,parseInt(o[3],10))/255,t);if(o=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(u))return n(o[4]),this.setRGB(Math.min(100,parseInt(o[1],10))/100,Math.min(100,parseInt(o[2],10))/100,Math.min(100,parseInt(o[3],10))/100,t);break;case"hsl":case"hsla":if(o=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(u))return n(o[4]),this.setHSL(parseFloat(o[1])/360,parseFloat(o[2])/100,parseFloat(o[3])/100,t);break;default:console.warn("THREE.Color: Unknown color model "+e)}}else if(a=/^\#([A-Fa-f\d]+)$/.exec(e)){const o=a[1],l=o.length;if(l===3)return this.setRGB(parseInt(o.charAt(0),16)/15,parseInt(o.charAt(1),16)/15,parseInt(o.charAt(2),16)/15,t);if(l===6)return this.setHex(parseInt(o,16),t);console.warn("THREE.Color: Invalid hex color "+e)}else if(e&&e.length>0)return this.setColorName(e,t);return this}setColorName(e,t=hn){const n=cu[e.toLowerCase()];return n!==void 0?this.setHex(n,t):console.warn("THREE.Color: Unknown color "+e),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(e){return this.r=e.r,this.g=e.g,this.b=e.b,this}copySRGBToLinear(e){return this.r=$n(e.r),this.g=$n(e.g),this.b=$n(e.b),this}copyLinearToSRGB(e){return this.r=er(e.r),this.g=er(e.g),this.b=er(e.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(e=hn){return gt.workingToColorSpace(Qt.copy(this),e),Math.round(lt(Qt.r*255,0,255))*65536+Math.round(lt(Qt.g*255,0,255))*256+Math.round(lt(Qt.b*255,0,255))}getHexString(e=hn){return("000000"+this.getHex(e).toString(16)).slice(-6)}getHSL(e,t=gt.workingColorSpace){gt.workingToColorSpace(Qt.copy(this),t);const n=Qt.r,a=Qt.g,o=Qt.b,l=Math.max(n,a,o),u=Math.min(n,a,o);let p,f;const _=(u+l)/2;if(u===l)p=0,f=0;else{const v=l-u;switch(f=_<=.5?v/(l+u):v/(2-l-u),l){case n:p=(a-o)/v+(a<o?6:0);break;case a:p=(o-n)/v+2;break;case o:p=(n-a)/v+4;break}p/=6}return e.h=p,e.s=f,e.l=_,e}getRGB(e,t=gt.workingColorSpace){return gt.workingToColorSpace(Qt.copy(this),t),e.r=Qt.r,e.g=Qt.g,e.b=Qt.b,e}getStyle(e=hn){gt.workingToColorSpace(Qt.copy(this),e);const t=Qt.r,n=Qt.g,a=Qt.b;return e!==hn?`color(${e} ${t.toFixed(3)} ${n.toFixed(3)} ${a.toFixed(3)})`:`rgb(${Math.round(t*255)},${Math.round(n*255)},${Math.round(a*255)})`}offsetHSL(e,t,n){return this.getHSL(Qn),this.setHSL(Qn.h+e,Qn.s+t,Qn.l+n)}add(e){return this.r+=e.r,this.g+=e.g,this.b+=e.b,this}addColors(e,t){return this.r=e.r+t.r,this.g=e.g+t.g,this.b=e.b+t.b,this}addScalar(e){return this.r+=e,this.g+=e,this.b+=e,this}sub(e){return this.r=Math.max(0,this.r-e.r),this.g=Math.max(0,this.g-e.g),this.b=Math.max(0,this.b-e.b),this}multiply(e){return this.r*=e.r,this.g*=e.g,this.b*=e.b,this}multiplyScalar(e){return this.r*=e,this.g*=e,this.b*=e,this}lerp(e,t){return this.r+=(e.r-this.r)*t,this.g+=(e.g-this.g)*t,this.b+=(e.b-this.b)*t,this}lerpColors(e,t,n){return this.r=e.r+(t.r-e.r)*n,this.g=e.g+(t.g-e.g)*n,this.b=e.b+(t.b-e.b)*n,this}lerpHSL(e,t){this.getHSL(Qn),e.getHSL(rs);const n=sa(Qn.h,rs.h,t),a=sa(Qn.s,rs.s,t),o=sa(Qn.l,rs.l,t);return this.setHSL(n,a,o),this}setFromVector3(e){return this.r=e.x,this.g=e.y,this.b=e.z,this}applyMatrix3(e){const t=this.r,n=this.g,a=this.b,o=e.elements;return this.r=o[0]*t+o[3]*n+o[6]*a,this.g=o[1]*t+o[4]*n+o[7]*a,this.b=o[2]*t+o[5]*n+o[8]*a,this}equals(e){return e.r===this.r&&e.g===this.g&&e.b===this.b}fromArray(e,t=0){return this.r=e[t],this.g=e[t+1],this.b=e[t+2],this}toArray(e=[],t=0){return e[t]=this.r,e[t+1]=this.g,e[t+2]=this.b,e}fromBufferAttribute(e,t){return this.r=e.getX(t),this.g=e.getY(t),this.b=e.getZ(t),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}}const Qt=new ot;ot.NAMES=cu;let H_=0;class ar extends Li{constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:H_++}),this.uuid=Ar(),this.name="",this.type="Material",this.blending=Ji,this.side=oi,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=Ha,this.blendDst=Va,this.blendEquation=Ti,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new ot(0,0,0),this.blendAlpha=0,this.depthFunc=tr,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=Bc,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=Fi,this.stencilZFail=Fi,this.stencilZPass=Fi,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.allowOverride=!0,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(e){this._alphaTest>0!=e>0&&this.version++,this._alphaTest=e}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(e){if(e!==void 0)for(const t in e){const n=e[t];if(n===void 0){console.warn(`THREE.Material: parameter '${t}' has value of undefined.`);continue}const a=this[t];if(a===void 0){console.warn(`THREE.Material: '${t}' is not a property of THREE.${this.type}.`);continue}a&&a.isColor?a.set(n):a&&a.isVector3&&n&&n.isVector3?a.copy(n):this[t]=n}}toJSON(e){const t=e===void 0||typeof e=="string";t&&(e={textures:{},images:{}});const n={metadata:{version:4.7,type:"Material",generator:"Material.toJSON"}};n.uuid=this.uuid,n.type=this.type,this.name!==""&&(n.name=this.name),this.color&&this.color.isColor&&(n.color=this.color.getHex()),this.roughness!==void 0&&(n.roughness=this.roughness),this.metalness!==void 0&&(n.metalness=this.metalness),this.sheen!==void 0&&(n.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(n.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(n.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(n.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&this.emissiveIntensity!==1&&(n.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(n.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(n.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(n.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(n.shininess=this.shininess),this.clearcoat!==void 0&&(n.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(n.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(n.clearcoatMap=this.clearcoatMap.toJSON(e).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(n.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(e).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(n.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(e).uuid,n.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.dispersion!==void 0&&(n.dispersion=this.dispersion),this.iridescence!==void 0&&(n.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(n.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(n.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(n.iridescenceMap=this.iridescenceMap.toJSON(e).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(n.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(e).uuid),this.anisotropy!==void 0&&(n.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(n.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(n.anisotropyMap=this.anisotropyMap.toJSON(e).uuid),this.map&&this.map.isTexture&&(n.map=this.map.toJSON(e).uuid),this.matcap&&this.matcap.isTexture&&(n.matcap=this.matcap.toJSON(e).uuid),this.alphaMap&&this.alphaMap.isTexture&&(n.alphaMap=this.alphaMap.toJSON(e).uuid),this.lightMap&&this.lightMap.isTexture&&(n.lightMap=this.lightMap.toJSON(e).uuid,n.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(n.aoMap=this.aoMap.toJSON(e).uuid,n.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(n.bumpMap=this.bumpMap.toJSON(e).uuid,n.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(n.normalMap=this.normalMap.toJSON(e).uuid,n.normalMapType=this.normalMapType,n.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(n.displacementMap=this.displacementMap.toJSON(e).uuid,n.displacementScale=this.displacementScale,n.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(n.roughnessMap=this.roughnessMap.toJSON(e).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(n.metalnessMap=this.metalnessMap.toJSON(e).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(n.emissiveMap=this.emissiveMap.toJSON(e).uuid),this.specularMap&&this.specularMap.isTexture&&(n.specularMap=this.specularMap.toJSON(e).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(n.specularIntensityMap=this.specularIntensityMap.toJSON(e).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(n.specularColorMap=this.specularColorMap.toJSON(e).uuid),this.envMap&&this.envMap.isTexture&&(n.envMap=this.envMap.toJSON(e).uuid,this.combine!==void 0&&(n.combine=this.combine)),this.envMapRotation!==void 0&&(n.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(n.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(n.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(n.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(n.gradientMap=this.gradientMap.toJSON(e).uuid),this.transmission!==void 0&&(n.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(n.transmissionMap=this.transmissionMap.toJSON(e).uuid),this.thickness!==void 0&&(n.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(n.thicknessMap=this.thicknessMap.toJSON(e).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(n.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(n.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(n.size=this.size),this.shadowSide!==null&&(n.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(n.sizeAttenuation=this.sizeAttenuation),this.blending!==Ji&&(n.blending=this.blending),this.side!==oi&&(n.side=this.side),this.vertexColors===!0&&(n.vertexColors=!0),this.opacity<1&&(n.opacity=this.opacity),this.transparent===!0&&(n.transparent=!0),this.blendSrc!==Ha&&(n.blendSrc=this.blendSrc),this.blendDst!==Va&&(n.blendDst=this.blendDst),this.blendEquation!==Ti&&(n.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(n.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(n.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(n.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(n.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(n.blendAlpha=this.blendAlpha),this.depthFunc!==tr&&(n.depthFunc=this.depthFunc),this.depthTest===!1&&(n.depthTest=this.depthTest),this.depthWrite===!1&&(n.depthWrite=this.depthWrite),this.colorWrite===!1&&(n.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(n.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==Bc&&(n.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(n.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(n.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==Fi&&(n.stencilFail=this.stencilFail),this.stencilZFail!==Fi&&(n.stencilZFail=this.stencilZFail),this.stencilZPass!==Fi&&(n.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(n.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(n.rotation=this.rotation),this.polygonOffset===!0&&(n.polygonOffset=!0),this.polygonOffsetFactor!==0&&(n.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(n.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(n.linewidth=this.linewidth),this.dashSize!==void 0&&(n.dashSize=this.dashSize),this.gapSize!==void 0&&(n.gapSize=this.gapSize),this.scale!==void 0&&(n.scale=this.scale),this.dithering===!0&&(n.dithering=!0),this.alphaTest>0&&(n.alphaTest=this.alphaTest),this.alphaHash===!0&&(n.alphaHash=!0),this.alphaToCoverage===!0&&(n.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(n.premultipliedAlpha=!0),this.forceSinglePass===!0&&(n.forceSinglePass=!0),this.wireframe===!0&&(n.wireframe=!0),this.wireframeLinewidth>1&&(n.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(n.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(n.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(n.flatShading=!0),this.visible===!1&&(n.visible=!1),this.toneMapped===!1&&(n.toneMapped=!1),this.fog===!1&&(n.fog=!1),Object.keys(this.userData).length>0&&(n.userData=this.userData);function a(o){const l=[];for(const u in o){const p=o[u];delete p.metadata,l.push(p)}return l}if(t){const o=a(e.textures),l=a(e.images);o.length>0&&(n.textures=o),l.length>0&&(n.images=l)}return n}clone(){return new this.constructor().copy(this)}copy(e){this.name=e.name,this.blending=e.blending,this.side=e.side,this.vertexColors=e.vertexColors,this.opacity=e.opacity,this.transparent=e.transparent,this.blendSrc=e.blendSrc,this.blendDst=e.blendDst,this.blendEquation=e.blendEquation,this.blendSrcAlpha=e.blendSrcAlpha,this.blendDstAlpha=e.blendDstAlpha,this.blendEquationAlpha=e.blendEquationAlpha,this.blendColor.copy(e.blendColor),this.blendAlpha=e.blendAlpha,this.depthFunc=e.depthFunc,this.depthTest=e.depthTest,this.depthWrite=e.depthWrite,this.stencilWriteMask=e.stencilWriteMask,this.stencilFunc=e.stencilFunc,this.stencilRef=e.stencilRef,this.stencilFuncMask=e.stencilFuncMask,this.stencilFail=e.stencilFail,this.stencilZFail=e.stencilZFail,this.stencilZPass=e.stencilZPass,this.stencilWrite=e.stencilWrite;const t=e.clippingPlanes;let n=null;if(t!==null){const a=t.length;n=new Array(a);for(let o=0;o!==a;++o)n[o]=t[o].clone()}return this.clippingPlanes=n,this.clipIntersection=e.clipIntersection,this.clipShadows=e.clipShadows,this.shadowSide=e.shadowSide,this.colorWrite=e.colorWrite,this.precision=e.precision,this.polygonOffset=e.polygonOffset,this.polygonOffsetFactor=e.polygonOffsetFactor,this.polygonOffsetUnits=e.polygonOffsetUnits,this.dithering=e.dithering,this.alphaTest=e.alphaTest,this.alphaHash=e.alphaHash,this.alphaToCoverage=e.alphaToCoverage,this.premultipliedAlpha=e.premultipliedAlpha,this.forceSinglePass=e.forceSinglePass,this.visible=e.visible,this.toneMapped=e.toneMapped,this.userData=JSON.parse(JSON.stringify(e.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(e){e===!0&&this.version++}}class Bo extends ar{constructor(e){super(),this.isMeshBasicMaterial=!0,this.type="MeshBasicMaterial",this.color=new ot(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Fn,this.combine=$l,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.specularMap=e.specularMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.combine=e.combine,this.reflectivity=e.reflectivity,this.refractionRatio=e.refractionRatio,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.fog=e.fog,this}}const kt=new X,ss=new et;let V_=0;class Ln{constructor(e,t,n=!1){if(Array.isArray(e))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,Object.defineProperty(this,"id",{value:V_++}),this.name="",this.array=e,this.itemSize=t,this.count=e!==void 0?e.length/t:0,this.normalized=n,this.usage=zc,this.updateRanges=[],this.gpuType=jn,this.version=0}onUploadCallback(){}set needsUpdate(e){e===!0&&this.version++}setUsage(e){return this.usage=e,this}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}copy(e){return this.name=e.name,this.array=new e.array.constructor(e.array),this.itemSize=e.itemSize,this.count=e.count,this.normalized=e.normalized,this.usage=e.usage,this.gpuType=e.gpuType,this}copyAt(e,t,n){e*=this.itemSize,n*=t.itemSize;for(let a=0,o=this.itemSize;a<o;a++)this.array[e+a]=t.array[n+a];return this}copyArray(e){return this.array.set(e),this}applyMatrix3(e){if(this.itemSize===2)for(let t=0,n=this.count;t<n;t++)ss.fromBufferAttribute(this,t),ss.applyMatrix3(e),this.setXY(t,ss.x,ss.y);else if(this.itemSize===3)for(let t=0,n=this.count;t<n;t++)kt.fromBufferAttribute(this,t),kt.applyMatrix3(e),this.setXYZ(t,kt.x,kt.y,kt.z);return this}applyMatrix4(e){for(let t=0,n=this.count;t<n;t++)kt.fromBufferAttribute(this,t),kt.applyMatrix4(e),this.setXYZ(t,kt.x,kt.y,kt.z);return this}applyNormalMatrix(e){for(let t=0,n=this.count;t<n;t++)kt.fromBufferAttribute(this,t),kt.applyNormalMatrix(e),this.setXYZ(t,kt.x,kt.y,kt.z);return this}transformDirection(e){for(let t=0,n=this.count;t<n;t++)kt.fromBufferAttribute(this,t),kt.transformDirection(e),this.setXYZ(t,kt.x,kt.y,kt.z);return this}set(e,t=0){return this.array.set(e,t),this}getComponent(e,t){let n=this.array[e*this.itemSize+t];return this.normalized&&(n=fr(n,this.array)),n}setComponent(e,t,n){return this.normalized&&(n=rn(n,this.array)),this.array[e*this.itemSize+t]=n,this}getX(e){let t=this.array[e*this.itemSize];return this.normalized&&(t=fr(t,this.array)),t}setX(e,t){return this.normalized&&(t=rn(t,this.array)),this.array[e*this.itemSize]=t,this}getY(e){let t=this.array[e*this.itemSize+1];return this.normalized&&(t=fr(t,this.array)),t}setY(e,t){return this.normalized&&(t=rn(t,this.array)),this.array[e*this.itemSize+1]=t,this}getZ(e){let t=this.array[e*this.itemSize+2];return this.normalized&&(t=fr(t,this.array)),t}setZ(e,t){return this.normalized&&(t=rn(t,this.array)),this.array[e*this.itemSize+2]=t,this}getW(e){let t=this.array[e*this.itemSize+3];return this.normalized&&(t=fr(t,this.array)),t}setW(e,t){return this.normalized&&(t=rn(t,this.array)),this.array[e*this.itemSize+3]=t,this}setXY(e,t,n){return e*=this.itemSize,this.normalized&&(t=rn(t,this.array),n=rn(n,this.array)),this.array[e+0]=t,this.array[e+1]=n,this}setXYZ(e,t,n,a){return e*=this.itemSize,this.normalized&&(t=rn(t,this.array),n=rn(n,this.array),a=rn(a,this.array)),this.array[e+0]=t,this.array[e+1]=n,this.array[e+2]=a,this}setXYZW(e,t,n,a,o){return e*=this.itemSize,this.normalized&&(t=rn(t,this.array),n=rn(n,this.array),a=rn(a,this.array),o=rn(o,this.array)),this.array[e+0]=t,this.array[e+1]=n,this.array[e+2]=a,this.array[e+3]=o,this}onUpload(e){return this.onUploadCallback=e,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){const e={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(e.name=this.name),this.usage!==zc&&(e.usage=this.usage),e}}class lu extends Ln{constructor(e,t,n){super(new Uint16Array(e),t,n)}}class uu extends Ln{constructor(e,t,n){super(new Uint32Array(e),t,n)}}class Nt extends Ln{constructor(e,t,n){super(new Float32Array(e),t,n)}}let G_=0;const pn=new Ft,Ta=new Wt,Wi=new X,un=new Rr,gr=new Rr,$t=new X;class cn extends Li{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:G_++}),this.uuid=Ar(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(e){return Array.isArray(e)?this.index=new(au(e)?uu:lu)(e,1):this.index=e,this}setIndirect(e){return this.indirect=e,this}getIndirect(){return this.indirect}getAttribute(e){return this.attributes[e]}setAttribute(e,t){return this.attributes[e]=t,this}deleteAttribute(e){return delete this.attributes[e],this}hasAttribute(e){return this.attributes[e]!==void 0}addGroup(e,t,n=0){this.groups.push({start:e,count:t,materialIndex:n})}clearGroups(){this.groups=[]}setDrawRange(e,t){this.drawRange.start=e,this.drawRange.count=t}applyMatrix4(e){const t=this.attributes.position;t!==void 0&&(t.applyMatrix4(e),t.needsUpdate=!0);const n=this.attributes.normal;if(n!==void 0){const o=new it().getNormalMatrix(e);n.applyNormalMatrix(o),n.needsUpdate=!0}const a=this.attributes.tangent;return a!==void 0&&(a.transformDirection(e),a.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(e){return pn.makeRotationFromQuaternion(e),this.applyMatrix4(pn),this}rotateX(e){return pn.makeRotationX(e),this.applyMatrix4(pn),this}rotateY(e){return pn.makeRotationY(e),this.applyMatrix4(pn),this}rotateZ(e){return pn.makeRotationZ(e),this.applyMatrix4(pn),this}translate(e,t,n){return pn.makeTranslation(e,t,n),this.applyMatrix4(pn),this}scale(e,t,n){return pn.makeScale(e,t,n),this.applyMatrix4(pn),this}lookAt(e){return Ta.lookAt(e),Ta.updateMatrix(),this.applyMatrix4(Ta.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(Wi).negate(),this.translate(Wi.x,Wi.y,Wi.z),this}setFromPoints(e){const t=this.getAttribute("position");if(t===void 0){const n=[];for(let a=0,o=e.length;a<o;a++){const l=e[a];n.push(l.x,l.y,l.z||0)}this.setAttribute("position",new Nt(n,3))}else{const n=Math.min(e.length,t.count);for(let a=0;a<n;a++){const o=e[a];t.setXYZ(a,o.x,o.y,o.z||0)}e.length>t.count&&console.warn("THREE.BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),t.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new Rr);const e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new X(-1/0,-1/0,-1/0),new X(1/0,1/0,1/0));return}if(e!==void 0){if(this.boundingBox.setFromBufferAttribute(e),t)for(let n=0,a=t.length;n<a;n++){const o=t[n];un.setFromBufferAttribute(o),this.morphTargetsRelative?($t.addVectors(this.boundingBox.min,un.min),this.boundingBox.expandByPoint($t),$t.addVectors(this.boundingBox.max,un.max),this.boundingBox.expandByPoint($t)):(this.boundingBox.expandByPoint(un.min),this.boundingBox.expandByPoint(un.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new Us);const e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new X,1/0);return}if(e){const n=this.boundingSphere.center;if(un.setFromBufferAttribute(e),t)for(let o=0,l=t.length;o<l;o++){const u=t[o];gr.setFromBufferAttribute(u),this.morphTargetsRelative?($t.addVectors(un.min,gr.min),un.expandByPoint($t),$t.addVectors(un.max,gr.max),un.expandByPoint($t)):(un.expandByPoint(gr.min),un.expandByPoint(gr.max))}un.getCenter(n);let a=0;for(let o=0,l=e.count;o<l;o++)$t.fromBufferAttribute(e,o),a=Math.max(a,n.distanceToSquared($t));if(t)for(let o=0,l=t.length;o<l;o++){const u=t[o],p=this.morphTargetsRelative;for(let f=0,_=u.count;f<_;f++)$t.fromBufferAttribute(u,f),p&&(Wi.fromBufferAttribute(e,f),$t.add(Wi)),a=Math.max(a,n.distanceToSquared($t))}this.boundingSphere.radius=Math.sqrt(a),isNaN(this.boundingSphere.radius)&&console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){const e=this.index,t=this.attributes;if(e===null||t.position===void 0||t.normal===void 0||t.uv===void 0){console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}const n=t.position,a=t.normal,o=t.uv;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new Ln(new Float32Array(4*n.count),4));const l=this.getAttribute("tangent"),u=[],p=[];for(let q=0;q<n.count;q++)u[q]=new X,p[q]=new X;const f=new X,_=new X,v=new X,x=new et,E=new et,R=new et,C=new X,y=new X;function m(q,P,M){f.fromBufferAttribute(n,q),_.fromBufferAttribute(n,P),v.fromBufferAttribute(n,M),x.fromBufferAttribute(o,q),E.fromBufferAttribute(o,P),R.fromBufferAttribute(o,M),_.sub(f),v.sub(f),E.sub(x),R.sub(x);const O=1/(E.x*R.y-R.x*E.y);isFinite(O)&&(C.copy(_).multiplyScalar(R.y).addScaledVector(v,-E.y).multiplyScalar(O),y.copy(v).multiplyScalar(E.x).addScaledVector(_,-R.x).multiplyScalar(O),u[q].add(C),u[P].add(C),u[M].add(C),p[q].add(y),p[P].add(y),p[M].add(y))}let N=this.groups;N.length===0&&(N=[{start:0,count:e.count}]);for(let q=0,P=N.length;q<P;++q){const M=N[q],O=M.start,te=M.count;for(let ee=O,Z=O+te;ee<Z;ee+=3)m(e.getX(ee+0),e.getX(ee+1),e.getX(ee+2))}const I=new X,L=new X,B=new X,D=new X;function H(q){B.fromBufferAttribute(a,q),D.copy(B);const P=u[q];I.copy(P),I.sub(B.multiplyScalar(B.dot(P))).normalize(),L.crossVectors(D,P);const O=L.dot(p[q])<0?-1:1;l.setXYZW(q,I.x,I.y,I.z,O)}for(let q=0,P=N.length;q<P;++q){const M=N[q],O=M.start,te=M.count;for(let ee=O,Z=O+te;ee<Z;ee+=3)H(e.getX(ee+0)),H(e.getX(ee+1)),H(e.getX(ee+2))}}computeVertexNormals(){const e=this.index,t=this.getAttribute("position");if(t!==void 0){let n=this.getAttribute("normal");if(n===void 0)n=new Ln(new Float32Array(t.count*3),3),this.setAttribute("normal",n);else for(let x=0,E=n.count;x<E;x++)n.setXYZ(x,0,0,0);const a=new X,o=new X,l=new X,u=new X,p=new X,f=new X,_=new X,v=new X;if(e)for(let x=0,E=e.count;x<E;x+=3){const R=e.getX(x+0),C=e.getX(x+1),y=e.getX(x+2);a.fromBufferAttribute(t,R),o.fromBufferAttribute(t,C),l.fromBufferAttribute(t,y),_.subVectors(l,o),v.subVectors(a,o),_.cross(v),u.fromBufferAttribute(n,R),p.fromBufferAttribute(n,C),f.fromBufferAttribute(n,y),u.add(_),p.add(_),f.add(_),n.setXYZ(R,u.x,u.y,u.z),n.setXYZ(C,p.x,p.y,p.z),n.setXYZ(y,f.x,f.y,f.z)}else for(let x=0,E=t.count;x<E;x+=3)a.fromBufferAttribute(t,x+0),o.fromBufferAttribute(t,x+1),l.fromBufferAttribute(t,x+2),_.subVectors(l,o),v.subVectors(a,o),_.cross(v),n.setXYZ(x+0,_.x,_.y,_.z),n.setXYZ(x+1,_.x,_.y,_.z),n.setXYZ(x+2,_.x,_.y,_.z);this.normalizeNormals(),n.needsUpdate=!0}}normalizeNormals(){const e=this.attributes.normal;for(let t=0,n=e.count;t<n;t++)$t.fromBufferAttribute(e,t),$t.normalize(),e.setXYZ(t,$t.x,$t.y,$t.z)}toNonIndexed(){function e(u,p){const f=u.array,_=u.itemSize,v=u.normalized,x=new f.constructor(p.length*_);let E=0,R=0;for(let C=0,y=p.length;C<y;C++){u.isInterleavedBufferAttribute?E=p[C]*u.data.stride+u.offset:E=p[C]*_;for(let m=0;m<_;m++)x[R++]=f[E++]}return new Ln(x,_,v)}if(this.index===null)return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;const t=new cn,n=this.index.array,a=this.attributes;for(const u in a){const p=a[u],f=e(p,n);t.setAttribute(u,f)}const o=this.morphAttributes;for(const u in o){const p=[],f=o[u];for(let _=0,v=f.length;_<v;_++){const x=f[_],E=e(x,n);p.push(E)}t.morphAttributes[u]=p}t.morphTargetsRelative=this.morphTargetsRelative;const l=this.groups;for(let u=0,p=l.length;u<p;u++){const f=l[u];t.addGroup(f.start,f.count,f.materialIndex)}return t}toJSON(){const e={metadata:{version:4.7,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(e.uuid=this.uuid,e.type=this.type,this.name!==""&&(e.name=this.name),Object.keys(this.userData).length>0&&(e.userData=this.userData),this.parameters!==void 0){const p=this.parameters;for(const f in p)p[f]!==void 0&&(e[f]=p[f]);return e}e.data={attributes:{}};const t=this.index;t!==null&&(e.data.index={type:t.array.constructor.name,array:Array.prototype.slice.call(t.array)});const n=this.attributes;for(const p in n){const f=n[p];e.data.attributes[p]=f.toJSON(e.data)}const a={};let o=!1;for(const p in this.morphAttributes){const f=this.morphAttributes[p],_=[];for(let v=0,x=f.length;v<x;v++){const E=f[v];_.push(E.toJSON(e.data))}_.length>0&&(a[p]=_,o=!0)}o&&(e.data.morphAttributes=a,e.data.morphTargetsRelative=this.morphTargetsRelative);const l=this.groups;l.length>0&&(e.data.groups=JSON.parse(JSON.stringify(l)));const u=this.boundingSphere;return u!==null&&(e.data.boundingSphere=u.toJSON()),e}clone(){return new this.constructor().copy(this)}copy(e){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;const t={};this.name=e.name;const n=e.index;n!==null&&this.setIndex(n.clone());const a=e.attributes;for(const f in a){const _=a[f];this.setAttribute(f,_.clone(t))}const o=e.morphAttributes;for(const f in o){const _=[],v=o[f];for(let x=0,E=v.length;x<E;x++)_.push(v[x].clone(t));this.morphAttributes[f]=_}this.morphTargetsRelative=e.morphTargetsRelative;const l=e.groups;for(let f=0,_=l.length;f<_;f++){const v=l[f];this.addGroup(v.start,v.count,v.materialIndex)}const u=e.boundingBox;u!==null&&(this.boundingBox=u.clone());const p=e.boundingSphere;return p!==null&&(this.boundingSphere=p.clone()),this.drawRange.start=e.drawRange.start,this.drawRange.count=e.drawRange.count,this.userData=e.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}}const el=new Ft,xi=new Ns,as=new Us,tl=new X,os=new X,cs=new X,ls=new X,ba=new X,us=new X,nl=new X,hs=new X;class _n extends Wt{constructor(e=new cn,t=new Bo){super(),this.isMesh=!0,this.type="Mesh",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.count=1,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),e.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=e.morphTargetInfluences.slice()),e.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},e.morphTargetDictionary)),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}updateMorphTargets(){const t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){const a=t[n[0]];if(a!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let o=0,l=a.length;o<l;o++){const u=a[o].name||String(o);this.morphTargetInfluences.push(0),this.morphTargetDictionary[u]=o}}}}getVertexPosition(e,t){const n=this.geometry,a=n.attributes.position,o=n.morphAttributes.position,l=n.morphTargetsRelative;t.fromBufferAttribute(a,e);const u=this.morphTargetInfluences;if(o&&u){us.set(0,0,0);for(let p=0,f=o.length;p<f;p++){const _=u[p],v=o[p];_!==0&&(ba.fromBufferAttribute(v,e),l?us.addScaledVector(ba,_):us.addScaledVector(ba.sub(t),_))}t.add(us)}return t}raycast(e,t){const n=this.geometry,a=this.material,o=this.matrixWorld;a!==void 0&&(n.boundingSphere===null&&n.computeBoundingSphere(),as.copy(n.boundingSphere),as.applyMatrix4(o),xi.copy(e.ray).recast(e.near),!(as.containsPoint(xi.origin)===!1&&(xi.intersectSphere(as,tl)===null||xi.origin.distanceToSquared(tl)>(e.far-e.near)**2))&&(el.copy(o).invert(),xi.copy(e.ray).applyMatrix4(el),!(n.boundingBox!==null&&xi.intersectsBox(n.boundingBox)===!1)&&this._computeIntersections(e,t,xi)))}_computeIntersections(e,t,n){let a;const o=this.geometry,l=this.material,u=o.index,p=o.attributes.position,f=o.attributes.uv,_=o.attributes.uv1,v=o.attributes.normal,x=o.groups,E=o.drawRange;if(u!==null)if(Array.isArray(l))for(let R=0,C=x.length;R<C;R++){const y=x[R],m=l[y.materialIndex],N=Math.max(y.start,E.start),I=Math.min(u.count,Math.min(y.start+y.count,E.start+E.count));for(let L=N,B=I;L<B;L+=3){const D=u.getX(L),H=u.getX(L+1),q=u.getX(L+2);a=ds(this,m,e,n,f,_,v,D,H,q),a&&(a.faceIndex=Math.floor(L/3),a.face.materialIndex=y.materialIndex,t.push(a))}}else{const R=Math.max(0,E.start),C=Math.min(u.count,E.start+E.count);for(let y=R,m=C;y<m;y+=3){const N=u.getX(y),I=u.getX(y+1),L=u.getX(y+2);a=ds(this,l,e,n,f,_,v,N,I,L),a&&(a.faceIndex=Math.floor(y/3),t.push(a))}}else if(p!==void 0)if(Array.isArray(l))for(let R=0,C=x.length;R<C;R++){const y=x[R],m=l[y.materialIndex],N=Math.max(y.start,E.start),I=Math.min(p.count,Math.min(y.start+y.count,E.start+E.count));for(let L=N,B=I;L<B;L+=3){const D=L,H=L+1,q=L+2;a=ds(this,m,e,n,f,_,v,D,H,q),a&&(a.faceIndex=Math.floor(L/3),a.face.materialIndex=y.materialIndex,t.push(a))}}else{const R=Math.max(0,E.start),C=Math.min(p.count,E.start+E.count);for(let y=R,m=C;y<m;y+=3){const N=y,I=y+1,L=y+2;a=ds(this,l,e,n,f,_,v,N,I,L),a&&(a.faceIndex=Math.floor(y/3),t.push(a))}}}}function W_(r,e,t,n,a,o,l,u){let p;if(e.side===an?p=n.intersectTriangle(l,o,a,!0,u):p=n.intersectTriangle(a,o,l,e.side===oi,u),p===null)return null;hs.copy(u),hs.applyMatrix4(r.matrixWorld);const f=t.ray.origin.distanceTo(hs);return f<t.near||f>t.far?null:{distance:f,point:hs.clone(),object:r}}function ds(r,e,t,n,a,o,l,u,p,f){r.getVertexPosition(u,os),r.getVertexPosition(p,cs),r.getVertexPosition(f,ls);const _=W_(r,e,t,n,os,cs,ls,nl);if(_){const v=new X;Sn.getBarycoord(nl,os,cs,ls,v),a&&(_.uv=Sn.getInterpolatedAttribute(a,u,p,f,v,new et)),o&&(_.uv1=Sn.getInterpolatedAttribute(o,u,p,f,v,new et)),l&&(_.normal=Sn.getInterpolatedAttribute(l,u,p,f,v,new X),_.normal.dot(n.direction)>0&&_.normal.multiplyScalar(-1));const x={a:u,b:p,c:f,normal:new X,materialIndex:0};Sn.getNormal(os,cs,ls,x.normal),_.face=x,_.barycoord=v}return _}class Di extends cn{constructor(e=1,t=1,n=1,a=1,o=1,l=1){super(),this.type="BoxGeometry",this.parameters={width:e,height:t,depth:n,widthSegments:a,heightSegments:o,depthSegments:l};const u=this;a=Math.floor(a),o=Math.floor(o),l=Math.floor(l);const p=[],f=[],_=[],v=[];let x=0,E=0;R("z","y","x",-1,-1,n,t,e,l,o,0),R("z","y","x",1,-1,n,t,-e,l,o,1),R("x","z","y",1,1,e,n,t,a,l,2),R("x","z","y",1,-1,e,n,-t,a,l,3),R("x","y","z",1,-1,e,t,n,a,o,4),R("x","y","z",-1,-1,e,t,-n,a,o,5),this.setIndex(p),this.setAttribute("position",new Nt(f,3)),this.setAttribute("normal",new Nt(_,3)),this.setAttribute("uv",new Nt(v,2));function R(C,y,m,N,I,L,B,D,H,q,P){const M=L/H,O=B/q,te=L/2,ee=B/2,Z=D/2,he=H+1,ae=q+1;let Se=0,re=0;const Ae=new X;for(let De=0;De<ae;De++){const Ve=De*O-ee;for(let tt=0;tt<he;tt++){const xt=tt*M-te;Ae[C]=xt*N,Ae[y]=Ve*I,Ae[m]=Z,f.push(Ae.x,Ae.y,Ae.z),Ae[C]=0,Ae[y]=0,Ae[m]=D>0?1:-1,_.push(Ae.x,Ae.y,Ae.z),v.push(tt/H),v.push(1-De/q),Se+=1}}for(let De=0;De<q;De++)for(let Ve=0;Ve<H;Ve++){const tt=x+Ve+he*De,xt=x+Ve+he*(De+1),Ze=x+(Ve+1)+he*(De+1),ie=x+(Ve+1)+he*De;p.push(tt,xt,ie),p.push(xt,Ze,ie),re+=6}u.addGroup(E,re,P),E+=re,x+=Se}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new Di(e.width,e.height,e.depth,e.widthSegments,e.heightSegments,e.depthSegments)}}function sr(r){const e={};for(const t in r){e[t]={};for(const n in r[t]){const a=r[t][n];a&&(a.isColor||a.isMatrix3||a.isMatrix4||a.isVector2||a.isVector3||a.isVector4||a.isTexture||a.isQuaternion)?a.isRenderTargetTexture?(console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),e[t][n]=null):e[t][n]=a.clone():Array.isArray(a)?e[t][n]=a.slice():e[t][n]=a}}return e}function nn(r){const e={};for(let t=0;t<r.length;t++){const n=sr(r[t]);for(const a in n)e[a]=n[a]}return e}function X_(r){const e=[];for(let t=0;t<r.length;t++)e.push(r[t].clone());return e}function hu(r){const e=r.getRenderTarget();return e===null?r.outputColorSpace:e.isXRRenderTarget===!0?e.texture.colorSpace:gt.workingColorSpace}const j_={clone:sr,merge:nn};var $_=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,q_=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`;class ci extends ar{constructor(e){super(),this.isShaderMaterial=!0,this.type="ShaderMaterial",this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=$_,this.fragmentShader=q_,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,e!==void 0&&this.setValues(e)}copy(e){return super.copy(e),this.fragmentShader=e.fragmentShader,this.vertexShader=e.vertexShader,this.uniforms=sr(e.uniforms),this.uniformsGroups=X_(e.uniformsGroups),this.defines=Object.assign({},e.defines),this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.fog=e.fog,this.lights=e.lights,this.clipping=e.clipping,this.extensions=Object.assign({},e.extensions),this.glslVersion=e.glslVersion,this}toJSON(e){const t=super.toJSON(e);t.glslVersion=this.glslVersion,t.uniforms={};for(const a in this.uniforms){const l=this.uniforms[a].value;l&&l.isTexture?t.uniforms[a]={type:"t",value:l.toJSON(e).uuid}:l&&l.isColor?t.uniforms[a]={type:"c",value:l.getHex()}:l&&l.isVector2?t.uniforms[a]={type:"v2",value:l.toArray()}:l&&l.isVector3?t.uniforms[a]={type:"v3",value:l.toArray()}:l&&l.isVector4?t.uniforms[a]={type:"v4",value:l.toArray()}:l&&l.isMatrix3?t.uniforms[a]={type:"m3",value:l.toArray()}:l&&l.isMatrix4?t.uniforms[a]={type:"m4",value:l.toArray()}:t.uniforms[a]={value:l}}Object.keys(this.defines).length>0&&(t.defines=this.defines),t.vertexShader=this.vertexShader,t.fragmentShader=this.fragmentShader,t.lights=this.lights,t.clipping=this.clipping;const n={};for(const a in this.extensions)this.extensions[a]===!0&&(n[a]=!0);return Object.keys(n).length>0&&(t.extensions=n),t}}class du extends Wt{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new Ft,this.projectionMatrix=new Ft,this.projectionMatrixInverse=new Ft,this.coordinateSystem=Dn,this._reversedDepth=!1}get reversedDepth(){return this._reversedDepth}copy(e,t){return super.copy(e,t),this.matrixWorldInverse.copy(e.matrixWorldInverse),this.projectionMatrix.copy(e.projectionMatrix),this.projectionMatrixInverse.copy(e.projectionMatrixInverse),this.coordinateSystem=e.coordinateSystem,this}getWorldDirection(e){return super.getWorldDirection(e).negate()}updateMatrixWorld(e){super.updateMatrixWorld(e),this.matrixWorldInverse.copy(this.matrixWorld).invert()}updateWorldMatrix(e,t){super.updateWorldMatrix(e,t),this.matrixWorldInverse.copy(this.matrixWorld).invert()}clone(){return new this.constructor().copy(this)}}const ei=new X,il=new et,rl=new et;class mn extends du{constructor(e=50,t=1,n=.1,a=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=e,this.zoom=1,this.near=n,this.far=a,this.focus=10,this.aspect=t,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.fov=e.fov,this.zoom=e.zoom,this.near=e.near,this.far=e.far,this.focus=e.focus,this.aspect=e.aspect,this.view=e.view===null?null:Object.assign({},e.view),this.filmGauge=e.filmGauge,this.filmOffset=e.filmOffset,this}setFocalLength(e){const t=.5*this.getFilmHeight()/e;this.fov=Ao*2*Math.atan(t),this.updateProjectionMatrix()}getFocalLength(){const e=Math.tan(As*.5*this.fov);return .5*this.getFilmHeight()/e}getEffectiveFOV(){return Ao*2*Math.atan(Math.tan(As*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(e,t,n){ei.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),t.set(ei.x,ei.y).multiplyScalar(-e/ei.z),ei.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),n.set(ei.x,ei.y).multiplyScalar(-e/ei.z)}getViewSize(e,t){return this.getViewBounds(e,il,rl),t.subVectors(rl,il)}setViewOffset(e,t,n,a,o,l){this.aspect=e/t,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=n,this.view.offsetY=a,this.view.width=o,this.view.height=l,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const e=this.near;let t=e*Math.tan(As*.5*this.fov)/this.zoom,n=2*t,a=this.aspect*n,o=-.5*a;const l=this.view;if(this.view!==null&&this.view.enabled){const p=l.fullWidth,f=l.fullHeight;o+=l.offsetX*a/p,t-=l.offsetY*n/f,a*=l.width/p,n*=l.height/f}const u=this.filmOffset;u!==0&&(o+=e*u/this.getFilmWidth()),this.projectionMatrix.makePerspective(o,o+a,t,t-n,e,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){const t=super.toJSON(e);return t.object.fov=this.fov,t.object.zoom=this.zoom,t.object.near=this.near,t.object.far=this.far,t.object.focus=this.focus,t.object.aspect=this.aspect,this.view!==null&&(t.object.view=Object.assign({},this.view)),t.object.filmGauge=this.filmGauge,t.object.filmOffset=this.filmOffset,t}}const Xi=-90,ji=1;class Y_ extends Wt{constructor(e,t,n){super(),this.type="CubeCamera",this.renderTarget=n,this.coordinateSystem=null,this.activeMipmapLevel=0;const a=new mn(Xi,ji,e,t);a.layers=this.layers,this.add(a);const o=new mn(Xi,ji,e,t);o.layers=this.layers,this.add(o);const l=new mn(Xi,ji,e,t);l.layers=this.layers,this.add(l);const u=new mn(Xi,ji,e,t);u.layers=this.layers,this.add(u);const p=new mn(Xi,ji,e,t);p.layers=this.layers,this.add(p);const f=new mn(Xi,ji,e,t);f.layers=this.layers,this.add(f)}updateCoordinateSystem(){const e=this.coordinateSystem,t=this.children.concat(),[n,a,o,l,u,p]=t;for(const f of t)this.remove(f);if(e===Dn)n.up.set(0,1,0),n.lookAt(1,0,0),a.up.set(0,1,0),a.lookAt(-1,0,0),o.up.set(0,0,-1),o.lookAt(0,1,0),l.up.set(0,0,1),l.lookAt(0,-1,0),u.up.set(0,1,0),u.lookAt(0,0,1),p.up.set(0,1,0),p.lookAt(0,0,-1);else if(e===Ps)n.up.set(0,-1,0),n.lookAt(-1,0,0),a.up.set(0,-1,0),a.lookAt(1,0,0),o.up.set(0,0,1),o.lookAt(0,1,0),l.up.set(0,0,-1),l.lookAt(0,-1,0),u.up.set(0,-1,0),u.lookAt(0,0,1),p.up.set(0,-1,0),p.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+e);for(const f of t)this.add(f),f.updateMatrixWorld()}update(e,t){this.parent===null&&this.updateMatrixWorld();const{renderTarget:n,activeMipmapLevel:a}=this;this.coordinateSystem!==e.coordinateSystem&&(this.coordinateSystem=e.coordinateSystem,this.updateCoordinateSystem());const[o,l,u,p,f,_]=this.children,v=e.getRenderTarget(),x=e.getActiveCubeFace(),E=e.getActiveMipmapLevel(),R=e.xr.enabled;e.xr.enabled=!1;const C=n.texture.generateMipmaps;n.texture.generateMipmaps=!1,e.setRenderTarget(n,0,a),e.render(t,o),e.setRenderTarget(n,1,a),e.render(t,l),e.setRenderTarget(n,2,a),e.render(t,u),e.setRenderTarget(n,3,a),e.render(t,p),e.setRenderTarget(n,4,a),e.render(t,f),n.texture.generateMipmaps=C,e.setRenderTarget(n,5,a),e.render(t,_),e.setRenderTarget(v,x,E),e.xr.enabled=R,n.texture.needsPMREMUpdate=!0}}class fu extends on{constructor(e=[],t=nr,n,a,o,l,u,p,f,_){super(e,t,n,a,o,l,u,p,f,_),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(e){this.image=e}}class K_ extends Pi{constructor(e=1,t={}){super(e,e,t),this.isWebGLCubeRenderTarget=!0;const n={width:e,height:e,depth:1},a=[n,n,n,n,n,n];this.texture=new fu(a),this._setTextureOptions(t),this.texture.isRenderTargetTexture=!0}fromEquirectangularTexture(e,t){this.texture.type=t.type,this.texture.colorSpace=t.colorSpace,this.texture.generateMipmaps=t.generateMipmaps,this.texture.minFilter=t.minFilter,this.texture.magFilter=t.magFilter;const n={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},a=new Di(5,5,5),o=new ci({name:"CubemapFromEquirect",uniforms:sr(n.uniforms),vertexShader:n.vertexShader,fragmentShader:n.fragmentShader,side:an,blending:si});o.uniforms.tEquirect.value=t;const l=new _n(a,o),u=t.minFilter;return t.minFilter===Ai&&(t.minFilter=Pn),new Y_(1,10,this).update(e,l),t.minFilter=u,l.geometry.dispose(),l.material.dispose(),this}clear(e,t=!0,n=!0,a=!0){const o=e.getRenderTarget();for(let l=0;l<6;l++)e.setRenderTarget(this,l),e.clear(t,n,a);e.setRenderTarget(o)}}class fs extends Wt{constructor(){super(),this.isGroup=!0,this.type="Group"}}const Z_={type:"move"};class wa{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new fs,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new fs,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new X,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new X),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new fs,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new X,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new X),this._grip}dispatchEvent(e){return this._targetRay!==null&&this._targetRay.dispatchEvent(e),this._grip!==null&&this._grip.dispatchEvent(e),this._hand!==null&&this._hand.dispatchEvent(e),this}connect(e){if(e&&e.hand){const t=this._hand;if(t)for(const n of e.hand.values())this._getHandJoint(t,n)}return this.dispatchEvent({type:"connected",data:e}),this}disconnect(e){return this.dispatchEvent({type:"disconnected",data:e}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(e,t,n){let a=null,o=null,l=null;const u=this._targetRay,p=this._grip,f=this._hand;if(e&&t.session.visibilityState!=="visible-blurred"){if(f&&e.hand){l=!0;for(const C of e.hand.values()){const y=t.getJointPose(C,n),m=this._getHandJoint(f,C);y!==null&&(m.matrix.fromArray(y.transform.matrix),m.matrix.decompose(m.position,m.rotation,m.scale),m.matrixWorldNeedsUpdate=!0,m.jointRadius=y.radius),m.visible=y!==null}const _=f.joints["index-finger-tip"],v=f.joints["thumb-tip"],x=_.position.distanceTo(v.position),E=.02,R=.005;f.inputState.pinching&&x>E+R?(f.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:e.handedness,target:this})):!f.inputState.pinching&&x<=E-R&&(f.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:e.handedness,target:this}))}else p!==null&&e.gripSpace&&(o=t.getPose(e.gripSpace,n),o!==null&&(p.matrix.fromArray(o.transform.matrix),p.matrix.decompose(p.position,p.rotation,p.scale),p.matrixWorldNeedsUpdate=!0,o.linearVelocity?(p.hasLinearVelocity=!0,p.linearVelocity.copy(o.linearVelocity)):p.hasLinearVelocity=!1,o.angularVelocity?(p.hasAngularVelocity=!0,p.angularVelocity.copy(o.angularVelocity)):p.hasAngularVelocity=!1));u!==null&&(a=t.getPose(e.targetRaySpace,n),a===null&&o!==null&&(a=o),a!==null&&(u.matrix.fromArray(a.transform.matrix),u.matrix.decompose(u.position,u.rotation,u.scale),u.matrixWorldNeedsUpdate=!0,a.linearVelocity?(u.hasLinearVelocity=!0,u.linearVelocity.copy(a.linearVelocity)):u.hasLinearVelocity=!1,a.angularVelocity?(u.hasAngularVelocity=!0,u.angularVelocity.copy(a.angularVelocity)):u.hasAngularVelocity=!1,this.dispatchEvent(Z_)))}return u!==null&&(u.visible=a!==null),p!==null&&(p.visible=o!==null),f!==null&&(f.visible=l!==null),this}_getHandJoint(e,t){if(e.joints[t.jointName]===void 0){const n=new fs;n.matrixAutoUpdate=!1,n.visible=!1,e.joints[t.jointName]=n,e.add(n)}return e.joints[t.jointName]}}class zo{constructor(e,t=1,n=1e3){this.isFog=!0,this.name="",this.color=new ot(e),this.near=t,this.far=n}clone(){return new zo(this.color,this.near,this.far)}toJSON(){return{type:"Fog",name:this.name,color:this.color.getHex(),near:this.near,far:this.far}}}class J_ extends Wt{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new Fn,this.environmentIntensity=1,this.environmentRotation=new Fn,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(e,t){return super.copy(e,t),e.background!==null&&(this.background=e.background.clone()),e.environment!==null&&(this.environment=e.environment.clone()),e.fog!==null&&(this.fog=e.fog.clone()),this.backgroundBlurriness=e.backgroundBlurriness,this.backgroundIntensity=e.backgroundIntensity,this.backgroundRotation.copy(e.backgroundRotation),this.environmentIntensity=e.environmentIntensity,this.environmentRotation.copy(e.environmentRotation),e.overrideMaterial!==null&&(this.overrideMaterial=e.overrideMaterial.clone()),this.matrixAutoUpdate=e.matrixAutoUpdate,this}toJSON(e){const t=super.toJSON(e);return this.fog!==null&&(t.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(t.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(t.object.backgroundIntensity=this.backgroundIntensity),t.object.backgroundRotation=this.backgroundRotation.toArray(),this.environmentIntensity!==1&&(t.object.environmentIntensity=this.environmentIntensity),t.object.environmentRotation=this.environmentRotation.toArray(),t}}const Aa=new X,Q_=new X,eg=new it;class ti{constructor(e=new X(1,0,0),t=0){this.isPlane=!0,this.normal=e,this.constant=t}set(e,t){return this.normal.copy(e),this.constant=t,this}setComponents(e,t,n,a){return this.normal.set(e,t,n),this.constant=a,this}setFromNormalAndCoplanarPoint(e,t){return this.normal.copy(e),this.constant=-t.dot(this.normal),this}setFromCoplanarPoints(e,t,n){const a=Aa.subVectors(n,t).cross(Q_.subVectors(e,t)).normalize();return this.setFromNormalAndCoplanarPoint(a,e),this}copy(e){return this.normal.copy(e.normal),this.constant=e.constant,this}normalize(){const e=1/this.normal.length();return this.normal.multiplyScalar(e),this.constant*=e,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(e){return this.normal.dot(e)+this.constant}distanceToSphere(e){return this.distanceToPoint(e.center)-e.radius}projectPoint(e,t){return t.copy(e).addScaledVector(this.normal,-this.distanceToPoint(e))}intersectLine(e,t){const n=e.delta(Aa),a=this.normal.dot(n);if(a===0)return this.distanceToPoint(e.start)===0?t.copy(e.start):null;const o=-(e.start.dot(this.normal)+this.constant)/a;return o<0||o>1?null:t.copy(e.start).addScaledVector(n,o)}intersectsLine(e){const t=this.distanceToPoint(e.start),n=this.distanceToPoint(e.end);return t<0&&n>0||n<0&&t>0}intersectsBox(e){return e.intersectsPlane(this)}intersectsSphere(e){return e.intersectsPlane(this)}coplanarPoint(e){return e.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(e,t){const n=t||eg.getNormalMatrix(e),a=this.coplanarPoint(Aa).applyMatrix4(e),o=this.normal.applyMatrix3(n).normalize();return this.constant=-a.dot(o),this}translate(e){return this.constant-=e.dot(this.normal),this}equals(e){return e.normal.equals(this.normal)&&e.constant===this.constant}clone(){return new this.constructor().copy(this)}}const yi=new Us,tg=new et(.5,.5),ps=new X;class Ho{constructor(e=new ti,t=new ti,n=new ti,a=new ti,o=new ti,l=new ti){this.planes=[e,t,n,a,o,l]}set(e,t,n,a,o,l){const u=this.planes;return u[0].copy(e),u[1].copy(t),u[2].copy(n),u[3].copy(a),u[4].copy(o),u[5].copy(l),this}copy(e){const t=this.planes;for(let n=0;n<6;n++)t[n].copy(e.planes[n]);return this}setFromProjectionMatrix(e,t=Dn,n=!1){const a=this.planes,o=e.elements,l=o[0],u=o[1],p=o[2],f=o[3],_=o[4],v=o[5],x=o[6],E=o[7],R=o[8],C=o[9],y=o[10],m=o[11],N=o[12],I=o[13],L=o[14],B=o[15];if(a[0].setComponents(f-l,E-_,m-R,B-N).normalize(),a[1].setComponents(f+l,E+_,m+R,B+N).normalize(),a[2].setComponents(f+u,E+v,m+C,B+I).normalize(),a[3].setComponents(f-u,E-v,m-C,B-I).normalize(),n)a[4].setComponents(p,x,y,L).normalize(),a[5].setComponents(f-p,E-x,m-y,B-L).normalize();else if(a[4].setComponents(f-p,E-x,m-y,B-L).normalize(),t===Dn)a[5].setComponents(f+p,E+x,m+y,B+L).normalize();else if(t===Ps)a[5].setComponents(p,x,y,L).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+t);return this}intersectsObject(e){if(e.boundingSphere!==void 0)e.boundingSphere===null&&e.computeBoundingSphere(),yi.copy(e.boundingSphere).applyMatrix4(e.matrixWorld);else{const t=e.geometry;t.boundingSphere===null&&t.computeBoundingSphere(),yi.copy(t.boundingSphere).applyMatrix4(e.matrixWorld)}return this.intersectsSphere(yi)}intersectsSprite(e){yi.center.set(0,0,0);const t=tg.distanceTo(e.center);return yi.radius=.7071067811865476+t,yi.applyMatrix4(e.matrixWorld),this.intersectsSphere(yi)}intersectsSphere(e){const t=this.planes,n=e.center,a=-e.radius;for(let o=0;o<6;o++)if(t[o].distanceToPoint(n)<a)return!1;return!0}intersectsBox(e){const t=this.planes;for(let n=0;n<6;n++){const a=t[n];if(ps.x=a.normal.x>0?e.max.x:e.min.x,ps.y=a.normal.y>0?e.max.y:e.min.y,ps.z=a.normal.z>0?e.max.z:e.min.z,a.distanceToPoint(ps)<0)return!1}return!0}containsPoint(e){const t=this.planes;for(let n=0;n<6;n++)if(t[n].distanceToPoint(e)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}}class Vo extends ar{constructor(e){super(),this.isLineBasicMaterial=!0,this.type="LineBasicMaterial",this.color=new ot(16777215),this.map=null,this.linewidth=1,this.linecap="round",this.linejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.linewidth=e.linewidth,this.linecap=e.linecap,this.linejoin=e.linejoin,this.fog=e.fog,this}}const Ls=new X,Is=new X,sl=new Ft,vr=new Ns,ms=new Us,Ra=new X,al=new X;class pu extends Wt{constructor(e=new cn,t=new Vo){super(),this.isLine=!0,this.type="Line",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}computeLineDistances(){const e=this.geometry;if(e.index===null){const t=e.attributes.position,n=[0];for(let a=1,o=t.count;a<o;a++)Ls.fromBufferAttribute(t,a-1),Is.fromBufferAttribute(t,a),n[a]=n[a-1],n[a]+=Ls.distanceTo(Is);e.setAttribute("lineDistance",new Nt(n,1))}else console.warn("THREE.Line.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}raycast(e,t){const n=this.geometry,a=this.matrixWorld,o=e.params.Line.threshold,l=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),ms.copy(n.boundingSphere),ms.applyMatrix4(a),ms.radius+=o,e.ray.intersectsSphere(ms)===!1)return;sl.copy(a).invert(),vr.copy(e.ray).applyMatrix4(sl);const u=o/((this.scale.x+this.scale.y+this.scale.z)/3),p=u*u,f=this.isLineSegments?2:1,_=n.index,x=n.attributes.position;if(_!==null){const E=Math.max(0,l.start),R=Math.min(_.count,l.start+l.count);for(let C=E,y=R-1;C<y;C+=f){const m=_.getX(C),N=_.getX(C+1),I=_s(this,e,vr,p,m,N,C);I&&t.push(I)}if(this.isLineLoop){const C=_.getX(R-1),y=_.getX(E),m=_s(this,e,vr,p,C,y,R-1);m&&t.push(m)}}else{const E=Math.max(0,l.start),R=Math.min(x.count,l.start+l.count);for(let C=E,y=R-1;C<y;C+=f){const m=_s(this,e,vr,p,C,C+1,C);m&&t.push(m)}if(this.isLineLoop){const C=_s(this,e,vr,p,R-1,E,R-1);C&&t.push(C)}}}updateMorphTargets(){const t=this.geometry.morphAttributes,n=Object.keys(t);if(n.length>0){const a=t[n[0]];if(a!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let o=0,l=a.length;o<l;o++){const u=a[o].name||String(o);this.morphTargetInfluences.push(0),this.morphTargetDictionary[u]=o}}}}}function _s(r,e,t,n,a,o,l){const u=r.geometry.attributes.position;if(Ls.fromBufferAttribute(u,a),Is.fromBufferAttribute(u,o),t.distanceSqToSegment(Ls,Is,Ra,al)>n)return;Ra.applyMatrix4(r.matrixWorld);const f=e.ray.origin.distanceTo(Ra);if(!(f<e.near||f>e.far))return{distance:f,point:al.clone().applyMatrix4(r.matrixWorld),index:l,face:null,faceIndex:null,barycoord:null,object:r}}const ol=new X,cl=new X;class ng extends pu{constructor(e,t){super(e,t),this.isLineSegments=!0,this.type="LineSegments"}computeLineDistances(){const e=this.geometry;if(e.index===null){const t=e.attributes.position,n=[];for(let a=0,o=t.count;a<o;a+=2)ol.fromBufferAttribute(t,a),cl.fromBufferAttribute(t,a+1),n[a]=a===0?0:n[a-1],n[a+1]=n[a]+ol.distanceTo(cl);e.setAttribute("lineDistance",new Nt(n,1))}else console.warn("THREE.LineSegments.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}}class mu extends on{constructor(e,t,n=Ri,a,o,l,u=Tn,p=Tn,f,_=Tr,v=1){if(_!==Tr&&_!==br)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");const x={width:e,height:t,depth:v};super(x,a,o,l,u,p,_,n,f),this.isDepthTexture=!0,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(e){return super.copy(e),this.source=new Oo(Object.assign({},e.image)),this.compareFunction=e.compareFunction,this}toJSON(e){const t=super.toJSON(e);return this.compareFunction!==null&&(t.compareFunction=this.compareFunction),t}}class Go extends cn{constructor(e=1,t=1,n=4,a=8,o=1){super(),this.type="CapsuleGeometry",this.parameters={radius:e,height:t,capSegments:n,radialSegments:a,heightSegments:o},t=Math.max(0,t),n=Math.max(1,Math.floor(n)),a=Math.max(3,Math.floor(a)),o=Math.max(1,Math.floor(o));const l=[],u=[],p=[],f=[],_=t/2,v=Math.PI/2*e,x=t,E=2*v+x,R=n*2+o,C=a+1,y=new X,m=new X;for(let N=0;N<=R;N++){let I=0,L=0,B=0,D=0;if(N<=n){const P=N/n,M=P*Math.PI/2;L=-_-e*Math.cos(M),B=e*Math.sin(M),D=-e*Math.cos(M),I=P*v}else if(N<=n+o){const P=(N-n)/o;L=-_+P*t,B=e,D=0,I=v+P*x}else{const P=(N-n-o)/n,M=P*Math.PI/2;L=_+e*Math.sin(M),B=e*Math.cos(M),D=e*Math.sin(M),I=v+x+P*v}const H=Math.max(0,Math.min(1,I/E));let q=0;N===0?q=.5/a:N===R&&(q=-.5/a);for(let P=0;P<=a;P++){const M=P/a,O=M*Math.PI*2,te=Math.sin(O),ee=Math.cos(O);m.x=-B*ee,m.y=L,m.z=B*te,u.push(m.x,m.y,m.z),y.set(-B*ee,D,B*te),y.normalize(),p.push(y.x,y.y,y.z),f.push(M+q,H)}if(N>0){const P=(N-1)*C;for(let M=0;M<a;M++){const O=P+M,te=P+M+1,ee=N*C+M,Z=N*C+M+1;l.push(O,te,ee),l.push(te,Z,ee)}}}this.setIndex(l),this.setAttribute("position",new Nt(u,3)),this.setAttribute("normal",new Nt(p,3)),this.setAttribute("uv",new Nt(f,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new Go(e.radius,e.height,e.capSegments,e.radialSegments,e.heightSegments)}}class Os extends cn{constructor(e=1,t=1,n=1,a=32,o=1,l=!1,u=0,p=Math.PI*2){super(),this.type="CylinderGeometry",this.parameters={radiusTop:e,radiusBottom:t,height:n,radialSegments:a,heightSegments:o,openEnded:l,thetaStart:u,thetaLength:p};const f=this;a=Math.floor(a),o=Math.floor(o);const _=[],v=[],x=[],E=[];let R=0;const C=[],y=n/2;let m=0;N(),l===!1&&(e>0&&I(!0),t>0&&I(!1)),this.setIndex(_),this.setAttribute("position",new Nt(v,3)),this.setAttribute("normal",new Nt(x,3)),this.setAttribute("uv",new Nt(E,2));function N(){const L=new X,B=new X;let D=0;const H=(t-e)/n;for(let q=0;q<=o;q++){const P=[],M=q/o,O=M*(t-e)+e;for(let te=0;te<=a;te++){const ee=te/a,Z=ee*p+u,he=Math.sin(Z),ae=Math.cos(Z);B.x=O*he,B.y=-M*n+y,B.z=O*ae,v.push(B.x,B.y,B.z),L.set(he,H,ae).normalize(),x.push(L.x,L.y,L.z),E.push(ee,1-M),P.push(R++)}C.push(P)}for(let q=0;q<a;q++)for(let P=0;P<o;P++){const M=C[P][q],O=C[P+1][q],te=C[P+1][q+1],ee=C[P][q+1];(e>0||P!==0)&&(_.push(M,O,ee),D+=3),(t>0||P!==o-1)&&(_.push(O,te,ee),D+=3)}f.addGroup(m,D,0),m+=D}function I(L){const B=R,D=new et,H=new X;let q=0;const P=L===!0?e:t,M=L===!0?1:-1;for(let te=1;te<=a;te++)v.push(0,y*M,0),x.push(0,M,0),E.push(.5,.5),R++;const O=R;for(let te=0;te<=a;te++){const Z=te/a*p+u,he=Math.cos(Z),ae=Math.sin(Z);H.x=P*ae,H.y=y*M,H.z=P*he,v.push(H.x,H.y,H.z),x.push(0,M,0),D.x=he*.5+.5,D.y=ae*.5*M+.5,E.push(D.x,D.y),R++}for(let te=0;te<a;te++){const ee=B+te,Z=O+te;L===!0?_.push(Z,Z+1,ee):_.push(Z+1,Z,ee),q+=3}f.addGroup(m,q,L===!0?1:2),m+=q}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new Os(e.radiusTop,e.radiusBottom,e.height,e.radialSegments,e.heightSegments,e.openEnded,e.thetaStart,e.thetaLength)}}class Wo extends Os{constructor(e=1,t=1,n=32,a=1,o=!1,l=0,u=Math.PI*2){super(0,e,t,n,a,o,l,u),this.type="ConeGeometry",this.parameters={radius:e,height:t,radialSegments:n,heightSegments:a,openEnded:o,thetaStart:l,thetaLength:u}}static fromJSON(e){return new Wo(e.radius,e.height,e.radialSegments,e.heightSegments,e.openEnded,e.thetaStart,e.thetaLength)}}class Cr extends cn{constructor(e=1,t=1,n=1,a=1){super(),this.type="PlaneGeometry",this.parameters={width:e,height:t,widthSegments:n,heightSegments:a};const o=e/2,l=t/2,u=Math.floor(n),p=Math.floor(a),f=u+1,_=p+1,v=e/u,x=t/p,E=[],R=[],C=[],y=[];for(let m=0;m<_;m++){const N=m*x-l;for(let I=0;I<f;I++){const L=I*v-o;R.push(L,-N,0),C.push(0,0,1),y.push(I/u),y.push(1-m/p)}}for(let m=0;m<p;m++)for(let N=0;N<u;N++){const I=N+f*m,L=N+f*(m+1),B=N+1+f*(m+1),D=N+1+f*m;E.push(I,L,D),E.push(L,B,D)}this.setIndex(E),this.setAttribute("position",new Nt(R,3)),this.setAttribute("normal",new Nt(C,3)),this.setAttribute("uv",new Nt(y,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new Cr(e.width,e.height,e.widthSegments,e.heightSegments)}}class Er extends cn{constructor(e=1,t=32,n=16,a=0,o=Math.PI*2,l=0,u=Math.PI){super(),this.type="SphereGeometry",this.parameters={radius:e,widthSegments:t,heightSegments:n,phiStart:a,phiLength:o,thetaStart:l,thetaLength:u},t=Math.max(3,Math.floor(t)),n=Math.max(2,Math.floor(n));const p=Math.min(l+u,Math.PI);let f=0;const _=[],v=new X,x=new X,E=[],R=[],C=[],y=[];for(let m=0;m<=n;m++){const N=[],I=m/n;let L=0;m===0&&l===0?L=.5/t:m===n&&p===Math.PI&&(L=-.5/t);for(let B=0;B<=t;B++){const D=B/t;v.x=-e*Math.cos(a+D*o)*Math.sin(l+I*u),v.y=e*Math.cos(l+I*u),v.z=e*Math.sin(a+D*o)*Math.sin(l+I*u),R.push(v.x,v.y,v.z),x.copy(v).normalize(),C.push(x.x,x.y,x.z),y.push(D+L,1-I),N.push(f++)}_.push(N)}for(let m=0;m<n;m++)for(let N=0;N<t;N++){const I=_[m][N+1],L=_[m][N],B=_[m+1][N],D=_[m+1][N+1];(m!==0||l>0)&&E.push(I,L,D),(m!==n-1||p<Math.PI)&&E.push(L,B,D)}this.setIndex(E),this.setAttribute("position",new Nt(R,3)),this.setAttribute("normal",new Nt(C,3)),this.setAttribute("uv",new Nt(y,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new Er(e.radius,e.widthSegments,e.heightSegments,e.phiStart,e.phiLength,e.thetaStart,e.thetaLength)}}class ll extends ar{constructor(e){super(),this.isMeshStandardMaterial=!0,this.type="MeshStandardMaterial",this.defines={STANDARD:""},this.color=new ot(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new ot(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=ru,this.normalScale=new et(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Fn,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.defines={STANDARD:""},this.color.copy(e.color),this.roughness=e.roughness,this.metalness=e.metalness,this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.emissive.copy(e.emissive),this.emissiveMap=e.emissiveMap,this.emissiveIntensity=e.emissiveIntensity,this.bumpMap=e.bumpMap,this.bumpScale=e.bumpScale,this.normalMap=e.normalMap,this.normalMapType=e.normalMapType,this.normalScale.copy(e.normalScale),this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.roughnessMap=e.roughnessMap,this.metalnessMap=e.metalnessMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.envMapIntensity=e.envMapIntensity,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.flatShading=e.flatShading,this.fog=e.fog,this}}class ig extends ar{constructor(e){super(),this.isMeshDepthMaterial=!0,this.type="MeshDepthMaterial",this.depthPacking=p_,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(e)}copy(e){return super.copy(e),this.depthPacking=e.depthPacking,this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this}}class rg extends ar{constructor(e){super(),this.isMeshDistanceMaterial=!0,this.type="MeshDistanceMaterial",this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(e)}copy(e){return super.copy(e),this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this}}class _u extends Wt{constructor(e,t=1){super(),this.isLight=!0,this.type="Light",this.color=new ot(e),this.intensity=t}dispose(){}copy(e,t){return super.copy(e,t),this.color.copy(e.color),this.intensity=e.intensity,this}toJSON(e){const t=super.toJSON(e);return t.object.color=this.color.getHex(),t.object.intensity=this.intensity,this.groundColor!==void 0&&(t.object.groundColor=this.groundColor.getHex()),this.distance!==void 0&&(t.object.distance=this.distance),this.angle!==void 0&&(t.object.angle=this.angle),this.decay!==void 0&&(t.object.decay=this.decay),this.penumbra!==void 0&&(t.object.penumbra=this.penumbra),this.shadow!==void 0&&(t.object.shadow=this.shadow.toJSON()),this.target!==void 0&&(t.object.target=this.target.uuid),t}}class sg extends _u{constructor(e,t,n){super(e,n),this.isHemisphereLight=!0,this.type="HemisphereLight",this.position.copy(Wt.DEFAULT_UP),this.updateMatrix(),this.groundColor=new ot(t)}copy(e,t){return super.copy(e,t),this.groundColor.copy(e.groundColor),this}}const Ca=new Ft,ul=new X,hl=new X;class ag{constructor(e){this.camera=e,this.intensity=1,this.bias=0,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new et(512,512),this.mapType=In,this.map=null,this.mapPass=null,this.matrix=new Ft,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new Ho,this._frameExtents=new et(1,1),this._viewportCount=1,this._viewports=[new Ut(0,0,1,1)]}getViewportCount(){return this._viewportCount}getFrustum(){return this._frustum}updateMatrices(e){const t=this.camera,n=this.matrix;ul.setFromMatrixPosition(e.matrixWorld),t.position.copy(ul),hl.setFromMatrixPosition(e.target.matrixWorld),t.lookAt(hl),t.updateMatrixWorld(),Ca.multiplyMatrices(t.projectionMatrix,t.matrixWorldInverse),this._frustum.setFromProjectionMatrix(Ca,t.coordinateSystem,t.reversedDepth),t.reversedDepth?n.set(.5,0,0,.5,0,.5,0,.5,0,0,1,0,0,0,0,1):n.set(.5,0,0,.5,0,.5,0,.5,0,0,.5,.5,0,0,0,1),n.multiply(Ca)}getViewport(e){return this._viewports[e]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(e){return this.camera=e.camera.clone(),this.intensity=e.intensity,this.bias=e.bias,this.radius=e.radius,this.autoUpdate=e.autoUpdate,this.needsUpdate=e.needsUpdate,this.normalBias=e.normalBias,this.blurSamples=e.blurSamples,this.mapSize.copy(e.mapSize),this}clone(){return new this.constructor().copy(this)}toJSON(){const e={};return this.intensity!==1&&(e.intensity=this.intensity),this.bias!==0&&(e.bias=this.bias),this.normalBias!==0&&(e.normalBias=this.normalBias),this.radius!==1&&(e.radius=this.radius),(this.mapSize.x!==512||this.mapSize.y!==512)&&(e.mapSize=this.mapSize.toArray()),e.camera=this.camera.toJSON(!1).object,delete e.camera.matrix,e}}class gu extends du{constructor(e=-1,t=1,n=1,a=-1,o=.1,l=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=e,this.right=t,this.top=n,this.bottom=a,this.near=o,this.far=l,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.left=e.left,this.right=e.right,this.top=e.top,this.bottom=e.bottom,this.near=e.near,this.far=e.far,this.zoom=e.zoom,this.view=e.view===null?null:Object.assign({},e.view),this}setViewOffset(e,t,n,a,o,l){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=n,this.view.offsetY=a,this.view.width=o,this.view.height=l,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const e=(this.right-this.left)/(2*this.zoom),t=(this.top-this.bottom)/(2*this.zoom),n=(this.right+this.left)/2,a=(this.top+this.bottom)/2;let o=n-e,l=n+e,u=a+t,p=a-t;if(this.view!==null&&this.view.enabled){const f=(this.right-this.left)/this.view.fullWidth/this.zoom,_=(this.top-this.bottom)/this.view.fullHeight/this.zoom;o+=f*this.view.offsetX,l=o+f*this.view.width,u-=_*this.view.offsetY,p=u-_*this.view.height}this.projectionMatrix.makeOrthographic(o,l,u,p,this.near,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){const t=super.toJSON(e);return t.object.zoom=this.zoom,t.object.left=this.left,t.object.right=this.right,t.object.top=this.top,t.object.bottom=this.bottom,t.object.near=this.near,t.object.far=this.far,this.view!==null&&(t.object.view=Object.assign({},this.view)),t}}class og extends ag{constructor(){super(new gu(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}}class dl extends _u{constructor(e,t){super(e,t),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(Wt.DEFAULT_UP),this.updateMatrix(),this.target=new Wt,this.shadow=new og}dispose(){this.shadow.dispose()}copy(e){return super.copy(e),this.target=e.target.clone(),this.shadow=e.shadow.clone(),this}}class cg extends mn{constructor(e=[]){super(),this.isArrayCamera=!0,this.isMultiViewCamera=!1,this.cameras=e}}const fl=new Ft;class lg{constructor(e,t,n=0,a=1/0){this.ray=new Ns(e,t),this.near=n,this.far=a,this.camera=null,this.layers=new ko,this.params={Mesh:{},Line:{threshold:1},LOD:{},Points:{threshold:1},Sprite:{}}}set(e,t){this.ray.set(e,t)}setFromCamera(e,t){t.isPerspectiveCamera?(this.ray.origin.setFromMatrixPosition(t.matrixWorld),this.ray.direction.set(e.x,e.y,.5).unproject(t).sub(this.ray.origin).normalize(),this.camera=t):t.isOrthographicCamera?(this.ray.origin.set(e.x,e.y,(t.near+t.far)/(t.near-t.far)).unproject(t),this.ray.direction.set(0,0,-1).transformDirection(t.matrixWorld),this.camera=t):console.error("THREE.Raycaster: Unsupported camera type: "+t.type)}setFromXRController(e){return fl.identity().extractRotation(e.matrixWorld),this.ray.origin.setFromMatrixPosition(e.matrixWorld),this.ray.direction.set(0,0,-1).applyMatrix4(fl),this}intersectObject(e,t=!0,n=[]){return Ro(e,this,n,t),n.sort(pl),n}intersectObjects(e,t=!0,n=[]){for(let a=0,o=e.length;a<o;a++)Ro(e[a],this,n,t);return n.sort(pl),n}}function pl(r,e){return r.distance-e.distance}function Ro(r,e,t,n){let a=!0;if(r.layers.test(e.layers)&&r.raycast(e,t)===!1&&(a=!1),a===!0&&n===!0){const o=r.children;for(let l=0,u=o.length;l<u;l++)Ro(o[l],e,t,!0)}}class ml{constructor(e=1,t=0,n=0){this.radius=e,this.phi=t,this.theta=n}set(e,t,n){return this.radius=e,this.phi=t,this.theta=n,this}copy(e){return this.radius=e.radius,this.phi=e.phi,this.theta=e.theta,this}makeSafe(){return this.phi=lt(this.phi,1e-6,Math.PI-1e-6),this}setFromVector3(e){return this.setFromCartesianCoords(e.x,e.y,e.z)}setFromCartesianCoords(e,t,n){return this.radius=Math.sqrt(e*e+t*t+n*n),this.radius===0?(this.theta=0,this.phi=0):(this.theta=Math.atan2(e,n),this.phi=Math.acos(lt(t/this.radius,-1,1))),this}clone(){return new this.constructor().copy(this)}}class ug extends ng{constructor(e=10,t=10,n=4473924,a=8947848){n=new ot(n),a=new ot(a);const o=t/2,l=e/t,u=e/2,p=[],f=[];for(let x=0,E=0,R=-u;x<=t;x++,R+=l){p.push(-u,0,R,u,0,R),p.push(R,0,-u,R,0,u);const C=x===o?n:a;C.toArray(f,E),E+=3,C.toArray(f,E),E+=3,C.toArray(f,E),E+=3,C.toArray(f,E),E+=3}const _=new cn;_.setAttribute("position",new Nt(p,3)),_.setAttribute("color",new Nt(f,3));const v=new Vo({vertexColors:!0,toneMapped:!1});super(_,v),this.type="GridHelper"}dispose(){this.geometry.dispose(),this.material.dispose()}}const _l=new X;let gs,Pa;class hg extends Wt{constructor(e=new X(0,0,1),t=new X(0,0,0),n=1,a=16776960,o=n*.2,l=o*.2){super(),this.type="ArrowHelper",gs===void 0&&(gs=new cn,gs.setAttribute("position",new Nt([0,0,0,0,1,0],3)),Pa=new Wo(.5,1,5,1),Pa.translate(0,-.5,0)),this.position.copy(t),this.line=new pu(gs,new Vo({color:a,toneMapped:!1})),this.line.matrixAutoUpdate=!1,this.add(this.line),this.cone=new _n(Pa,new Bo({color:a,toneMapped:!1})),this.cone.matrixAutoUpdate=!1,this.add(this.cone),this.setDirection(e),this.setLength(n,o,l)}setDirection(e){if(e.y>.99999)this.quaternion.set(0,0,0,1);else if(e.y<-.99999)this.quaternion.set(1,0,0,0);else{_l.set(e.z,0,-e.x).normalize();const t=Math.acos(e.y);this.quaternion.setFromAxisAngle(_l,t)}}setLength(e,t=e*.2,n=t*.2){this.line.scale.set(1,Math.max(1e-4,e-t),1),this.line.updateMatrix(),this.cone.scale.set(n,t,n),this.cone.position.y=e,this.cone.updateMatrix()}setColor(e){this.line.material.color.set(e),this.cone.material.color.set(e)}copy(e){return super.copy(e,!1),this.line.copy(e.line),this.cone.copy(e.cone),this}dispose(){this.line.geometry.dispose(),this.line.material.dispose(),this.cone.geometry.dispose(),this.cone.material.dispose()}}class dg extends Li{constructor(e,t=null){super(),this.object=e,this.domElement=t,this.enabled=!0,this.state=-1,this.keys={},this.mouseButtons={LEFT:null,MIDDLE:null,RIGHT:null},this.touches={ONE:null,TWO:null}}connect(e){if(e===void 0){console.warn("THREE.Controls: connect() now requires an element.");return}this.domElement!==null&&this.disconnect(),this.domElement=e}disconnect(){}dispose(){}update(){}}function gl(r,e,t,n){const a=fg(n);switch(t){case Ql:return r*e;case tu:return r*e/a.components*a.byteLength;case Fo:return r*e/a.components*a.byteLength;case nu:return r*e*2/a.components*a.byteLength;case Uo:return r*e*2/a.components*a.byteLength;case eu:return r*e*3/a.components*a.byteLength;case Mn:return r*e*4/a.components*a.byteLength;case No:return r*e*4/a.components*a.byteLength;case Ss:case Ms:return Math.floor((r+3)/4)*Math.floor((e+3)/4)*8;case Ts:case bs:return Math.floor((r+3)/4)*Math.floor((e+3)/4)*16;case to:case io:return Math.max(r,16)*Math.max(e,8)/4;case eo:case no:return Math.max(r,8)*Math.max(e,8)/2;case ro:case so:return Math.floor((r+3)/4)*Math.floor((e+3)/4)*8;case ao:return Math.floor((r+3)/4)*Math.floor((e+3)/4)*16;case oo:return Math.floor((r+3)/4)*Math.floor((e+3)/4)*16;case co:return Math.floor((r+4)/5)*Math.floor((e+3)/4)*16;case lo:return Math.floor((r+4)/5)*Math.floor((e+4)/5)*16;case uo:return Math.floor((r+5)/6)*Math.floor((e+4)/5)*16;case ho:return Math.floor((r+5)/6)*Math.floor((e+5)/6)*16;case fo:return Math.floor((r+7)/8)*Math.floor((e+4)/5)*16;case po:return Math.floor((r+7)/8)*Math.floor((e+5)/6)*16;case mo:return Math.floor((r+7)/8)*Math.floor((e+7)/8)*16;case _o:return Math.floor((r+9)/10)*Math.floor((e+4)/5)*16;case go:return Math.floor((r+9)/10)*Math.floor((e+5)/6)*16;case vo:return Math.floor((r+9)/10)*Math.floor((e+7)/8)*16;case xo:return Math.floor((r+9)/10)*Math.floor((e+9)/10)*16;case yo:return Math.floor((r+11)/12)*Math.floor((e+9)/10)*16;case Eo:return Math.floor((r+11)/12)*Math.floor((e+11)/12)*16;case ws:case So:case Mo:return Math.ceil(r/4)*Math.ceil(e/4)*16;case iu:case To:return Math.ceil(r/4)*Math.ceil(e/4)*8;case bo:case wo:return Math.ceil(r/4)*Math.ceil(e/4)*16}throw new Error(`Unable to determine texture byte length for ${t} format.`)}function fg(r){switch(r){case In:case Kl:return{byteLength:1,components:1};case Sr:case Zl:case wr:return{byteLength:2,components:1};case Lo:case Io:return{byteLength:2,components:4};case Ri:case Do:case jn:return{byteLength:4,components:1};case Jl:return{byteLength:4,components:3}}throw new Error(`Unknown texture type ${r}.`)}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:"179"}}));typeof window<"u"&&(window.__THREE__?console.warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__="179");function vu(){let r=null,e=!1,t=null,n=null;function a(o,l){t(o,l),n=r.requestAnimationFrame(a)}return{start:function(){e!==!0&&t!==null&&(n=r.requestAnimationFrame(a),e=!0)},stop:function(){r.cancelAnimationFrame(n),e=!1},setAnimationLoop:function(o){t=o},setContext:function(o){r=o}}}function pg(r){const e=new WeakMap;function t(u,p){const f=u.array,_=u.usage,v=f.byteLength,x=r.createBuffer();r.bindBuffer(p,x),r.bufferData(p,f,_),u.onUploadCallback();let E;if(f instanceof Float32Array)E=r.FLOAT;else if(typeof Float16Array<"u"&&f instanceof Float16Array)E=r.HALF_FLOAT;else if(f instanceof Uint16Array)u.isFloat16BufferAttribute?E=r.HALF_FLOAT:E=r.UNSIGNED_SHORT;else if(f instanceof Int16Array)E=r.SHORT;else if(f instanceof Uint32Array)E=r.UNSIGNED_INT;else if(f instanceof Int32Array)E=r.INT;else if(f instanceof Int8Array)E=r.BYTE;else if(f instanceof Uint8Array)E=r.UNSIGNED_BYTE;else if(f instanceof Uint8ClampedArray)E=r.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+f);return{buffer:x,type:E,bytesPerElement:f.BYTES_PER_ELEMENT,version:u.version,size:v}}function n(u,p,f){const _=p.array,v=p.updateRanges;if(r.bindBuffer(f,u),v.length===0)r.bufferSubData(f,0,_);else{v.sort((E,R)=>E.start-R.start);let x=0;for(let E=1;E<v.length;E++){const R=v[x],C=v[E];C.start<=R.start+R.count+1?R.count=Math.max(R.count,C.start+C.count-R.start):(++x,v[x]=C)}v.length=x+1;for(let E=0,R=v.length;E<R;E++){const C=v[E];r.bufferSubData(f,C.start*_.BYTES_PER_ELEMENT,_,C.start,C.count)}p.clearUpdateRanges()}p.onUploadCallback()}function a(u){return u.isInterleavedBufferAttribute&&(u=u.data),e.get(u)}function o(u){u.isInterleavedBufferAttribute&&(u=u.data);const p=e.get(u);p&&(r.deleteBuffer(p.buffer),e.delete(u))}function l(u,p){if(u.isInterleavedBufferAttribute&&(u=u.data),u.isGLBufferAttribute){const _=e.get(u);(!_||_.version<u.version)&&e.set(u,{buffer:u.buffer,type:u.type,bytesPerElement:u.elementSize,version:u.version});return}const f=e.get(u);if(f===void 0)e.set(u,t(u,p));else if(f.version<u.version){if(f.size!==u.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");n(f.buffer,u,p),f.version=u.version}}return{get:a,remove:o,update:l}}var mg=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,_g=`#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,gg=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,vg=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,xg=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,yg=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,Eg=`#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,Sg=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,Mg=`#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec3 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 ).rgb;
	}
#endif`,Tg=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,bg=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,wg=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,Ag=`float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,Rg=`#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,Cg=`#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,Pg=`#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`,Dg=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,Lg=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,Ig=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,Fg=`#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`,Ug=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`,Ng=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec3 vColor;
#endif`,Og=`#if defined( USE_COLOR_ALPHA )
	vColor = vec4( 1.0 );
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec3( 1.0 );
#endif
#ifdef USE_COLOR
	vColor *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.xyz *= instanceColor.xyz;
#endif
#ifdef USE_BATCHING_COLOR
	vec3 batchingColor = getBatchingColor( getIndirectIndex( gl_DrawID ) );
	vColor.xyz *= batchingColor.xyz;
#endif`,kg=`#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
mat3 transposeMat3( const in mat3 m ) {
	mat3 tmp;
	tmp[ 0 ] = vec3( m[ 0 ].x, m[ 1 ].x, m[ 2 ].x );
	tmp[ 1 ] = vec3( m[ 0 ].y, m[ 1 ].y, m[ 2 ].y );
	tmp[ 2 ] = vec3( m[ 0 ].z, m[ 1 ].z, m[ 2 ].z );
	return tmp;
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,Bg=`#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,zg=`vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`,Hg=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,Vg=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,Gg=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,Wg=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,Xg="gl_FragColor = linearToOutputTexel( gl_FragColor );",jg=`vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,$g=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
	#else
		vec4 envColor = vec4( 0.0 );
	#endif
	#ifdef ENVMAP_BLENDING_MULTIPLY
		outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_MIX )
		outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_ADD )
		outgoingLight += envColor.xyz * specularStrength * reflectivity;
	#endif
#endif`,qg=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`,Yg=`#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,Kg=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,Zg=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,Jg=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,Qg=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,ev=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,tv=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,nv=`#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,iv=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,rv=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,sv=`varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,av=`uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`,ov=`#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, roughness * roughness) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`,cv=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,lv=`varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,uv=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,hv=`varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,dv=`PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb * ( 1.0 - metalnessFactor );
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = mix( min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = mix( vec3( 0.04 ), diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.07, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,fv=`struct PhysicalMaterial {
	vec3 diffuseColor;
	float roughness;
	vec3 specularColor;
	float specularF90;
	float dispersion;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return saturate(v);
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColor;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transposeMat3( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float a = roughness < 0.25 ? -339.2 * r2 + 161.4 * roughness - 25.9 : -8.48 * r2 + 14.3 * roughness - 9.95;
	float b = roughness < 0.25 ? 44.0 * r2 - 23.7 * roughness + 3.26 : 1.97 * r2 - 3.27 * roughness + 0.72;
	float DG = exp( a * dotNV + b ) + ( roughness < 0.25 ? 0.0 : 0.1 * ( roughness - 0.25 ) );
	return saturate( DG * RECIPROCAL_PI );
}
vec2 DFGApprox( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	const vec4 c0 = vec4( - 1, - 0.0275, - 0.572, 0.022 );
	const vec4 c1 = vec4( 1, 0.0425, 1.04, - 0.04 );
	vec4 r = roughness * c0 + c1;
	float a004 = min( r.x * r.x, exp2( - 9.28 * dotNV ) ) * r.x + r.y;
	vec2 fab = vec2( - 1.04, 1.04 ) * a004 + r.zw;
	return fab;
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColor * t2.x + ( vec3( 1.0 ) - material.specularColor ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseColor * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
	#endif
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnel, material.roughness, singleScattering, multiScattering );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScattering, multiScattering );
	#endif
	vec3 totalScattering = singleScattering + multiScattering;
	vec3 diffuse = material.diffuseColor * ( 1.0 - max( max( totalScattering.r, totalScattering.g ), totalScattering.b ) );
	reflectedLight.indirectSpecular += radiance * singleScattering;
	reflectedLight.indirectSpecular += multiScattering * cosineWeightedIrradiance;
	reflectedLight.indirectDiffuse += diffuse * cosineWeightedIrradiance;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,pv=`
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnel = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,mv=`#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
		iblIrradiance += getIBLIrradiance( geometryNormal );
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,_v=`#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,gv=`#if defined( USE_LOGDEPTHBUF )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,vv=`#if defined( USE_LOGDEPTHBUF )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,xv=`#ifdef USE_LOGDEPTHBUF
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,yv=`#ifdef USE_LOGDEPTHBUF
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,Ev=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,Sv=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,Mv=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,Tv=`#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,bv=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,wv=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,Av=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,Rv=`#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,Cv=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,Pv=`#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`,Dv=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,Lv=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,Iv=`#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,Fv=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Uv=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Nv=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,Ov=`#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,kv=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,Bv=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,zv=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,Hv=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,Vv=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,Gv=`vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return depth * ( near - far ) - near;
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return ( near * far ) / ( ( far - near ) * depth - far );
}`,Wv=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,Xv=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,jv=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,$v=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,qv=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,Yv=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,Kv=`#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform sampler2D pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	float texture2DCompare( sampler2D depths, vec2 uv, float compare ) {
		float depth = unpackRGBAToDepth( texture2D( depths, uv ) );
		#ifdef USE_REVERSEDEPTHBUF
			return step( depth, compare );
		#else
			return step( compare, depth );
		#endif
	}
	vec2 texture2DDistribution( sampler2D shadow, vec2 uv ) {
		return unpackRGBATo2Half( texture2D( shadow, uv ) );
	}
	float VSMShadow (sampler2D shadow, vec2 uv, float compare ){
		float occlusion = 1.0;
		vec2 distribution = texture2DDistribution( shadow, uv );
		#ifdef USE_REVERSEDEPTHBUF
			float hard_shadow = step( distribution.x, compare );
		#else
			float hard_shadow = step( compare , distribution.x );
		#endif
		if (hard_shadow != 1.0 ) {
			float distance = compare - distribution.x ;
			float variance = max( 0.00000, distribution.y * distribution.y );
			float softness_probability = variance / (variance + distance * distance );			softness_probability = clamp( ( softness_probability - 0.3 ) / ( 0.95 - 0.3 ), 0.0, 1.0 );			occlusion = clamp( max( hard_shadow, softness_probability ), 0.0, 1.0 );
		}
		return occlusion;
	}
	float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
		float shadow = 1.0;
		shadowCoord.xyz /= shadowCoord.w;
		shadowCoord.z += shadowBias;
		bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
		bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
		if ( frustumTest ) {
		#if defined( SHADOWMAP_TYPE_PCF )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx0 = - texelSize.x * shadowRadius;
			float dy0 = - texelSize.y * shadowRadius;
			float dx1 = + texelSize.x * shadowRadius;
			float dy1 = + texelSize.y * shadowRadius;
			float dx2 = dx0 / 2.0;
			float dy2 = dy0 / 2.0;
			float dx3 = dx1 / 2.0;
			float dy3 = dy1 / 2.0;
			shadow = (
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy1 ), shadowCoord.z )
			) * ( 1.0 / 17.0 );
		#elif defined( SHADOWMAP_TYPE_PCF_SOFT )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx = texelSize.x;
			float dy = texelSize.y;
			vec2 uv = shadowCoord.xy;
			vec2 f = fract( uv * shadowMapSize + 0.5 );
			uv -= f * texelSize;
			shadow = (
				texture2DCompare( shadowMap, uv, shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( dx, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( 0.0, dy ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + texelSize, shadowCoord.z ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, 0.0 ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 0.0 ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, dy ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( 0.0, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 0.0, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( texture2DCompare( shadowMap, uv + vec2( dx, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( dx, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( mix( texture2DCompare( shadowMap, uv + vec2( -dx, -dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, -dy ), shadowCoord.z ),
						  f.x ),
					 mix( texture2DCompare( shadowMap, uv + vec2( -dx, 2.0 * dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 2.0 * dy ), shadowCoord.z ),
						  f.x ),
					 f.y )
			) * ( 1.0 / 9.0 );
		#elif defined( SHADOWMAP_TYPE_VSM )
			shadow = VSMShadow( shadowMap, shadowCoord.xy, shadowCoord.z );
		#else
			shadow = texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z );
		#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	vec2 cubeToUV( vec3 v, float texelSizeY ) {
		vec3 absV = abs( v );
		float scaleToCube = 1.0 / max( absV.x, max( absV.y, absV.z ) );
		absV *= scaleToCube;
		v *= scaleToCube * ( 1.0 - 2.0 * texelSizeY );
		vec2 planar = v.xy;
		float almostATexel = 1.5 * texelSizeY;
		float almostOne = 1.0 - almostATexel;
		if ( absV.z >= almostOne ) {
			if ( v.z > 0.0 )
				planar.x = 4.0 - v.x;
		} else if ( absV.x >= almostOne ) {
			float signX = sign( v.x );
			planar.x = v.z * signX + 2.0 * signX;
		} else if ( absV.y >= almostOne ) {
			float signY = sign( v.y );
			planar.x = v.x + 2.0 * signY + 2.0;
			planar.y = v.z * signY - 2.0;
		}
		return vec2( 0.125, 0.25 ) * planar + vec2( 0.375, 0.75 );
	}
	float getPointShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		
		float lightToPositionLength = length( lightToPosition );
		if ( lightToPositionLength - shadowCameraFar <= 0.0 && lightToPositionLength - shadowCameraNear >= 0.0 ) {
			float dp = ( lightToPositionLength - shadowCameraNear ) / ( shadowCameraFar - shadowCameraNear );			dp += shadowBias;
			vec3 bd3D = normalize( lightToPosition );
			vec2 texelSize = vec2( 1.0 ) / ( shadowMapSize * vec2( 4.0, 2.0 ) );
			#if defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_PCF_SOFT ) || defined( SHADOWMAP_TYPE_VSM )
				vec2 offset = vec2( - 1, 1 ) * shadowRadius * texelSize.y;
				shadow = (
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxx, texelSize.y ), dp )
				) * ( 1.0 / 9.0 );
			#else
				shadow = texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp );
			#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
#endif`,Zv=`#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,Jv=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,Qv=`float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,e0=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,t0=`#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,n0=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,i0=`#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,r0=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,s0=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,a0=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,o0=`#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,c0=`#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseColor, material.specularColor, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,l0=`#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		#else
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,u0=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,h0=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,d0=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,f0=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`;const p0=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,m0=`uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,_0=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,g0=`#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,v0=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,x0=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,y0=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,E0=`#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	#ifdef USE_REVERSEDEPTHBUF
		float fragCoordZ = vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ];
	#else
		float fragCoordZ = 0.5 * vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ] + 0.5;
	#endif
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`,S0=`#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,M0=`#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = packDepthToRGBA( dist );
}`,T0=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,b0=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,w0=`uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,A0=`uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,R0=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,C0=`uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,P0=`#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,D0=`#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,L0=`#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,I0=`#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,F0=`#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,U0=`#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <packing>
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( packNormalToRGB( normal ), diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,N0=`#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,O0=`#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,k0=`#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,B0=`#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
		float sheenEnergyComp = 1.0 - 0.157 * max3( material.sheenColor );
		outgoingLight = outgoingLight * sheenEnergyComp + sheenSpecularDirect + sheenSpecularIndirect;
	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,z0=`#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,H0=`#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,V0=`uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,G0=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,W0=`#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,X0=`uniform vec3 color;
uniform float opacity;
#include <common>
#include <packing>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,j0=`uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,$0=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,at={alphahash_fragment:mg,alphahash_pars_fragment:_g,alphamap_fragment:gg,alphamap_pars_fragment:vg,alphatest_fragment:xg,alphatest_pars_fragment:yg,aomap_fragment:Eg,aomap_pars_fragment:Sg,batching_pars_vertex:Mg,batching_vertex:Tg,begin_vertex:bg,beginnormal_vertex:wg,bsdfs:Ag,iridescence_fragment:Rg,bumpmap_pars_fragment:Cg,clipping_planes_fragment:Pg,clipping_planes_pars_fragment:Dg,clipping_planes_pars_vertex:Lg,clipping_planes_vertex:Ig,color_fragment:Fg,color_pars_fragment:Ug,color_pars_vertex:Ng,color_vertex:Og,common:kg,cube_uv_reflection_fragment:Bg,defaultnormal_vertex:zg,displacementmap_pars_vertex:Hg,displacementmap_vertex:Vg,emissivemap_fragment:Gg,emissivemap_pars_fragment:Wg,colorspace_fragment:Xg,colorspace_pars_fragment:jg,envmap_fragment:$g,envmap_common_pars_fragment:qg,envmap_pars_fragment:Yg,envmap_pars_vertex:Kg,envmap_physical_pars_fragment:ov,envmap_vertex:Zg,fog_vertex:Jg,fog_pars_vertex:Qg,fog_fragment:ev,fog_pars_fragment:tv,gradientmap_pars_fragment:nv,lightmap_pars_fragment:iv,lights_lambert_fragment:rv,lights_lambert_pars_fragment:sv,lights_pars_begin:av,lights_toon_fragment:cv,lights_toon_pars_fragment:lv,lights_phong_fragment:uv,lights_phong_pars_fragment:hv,lights_physical_fragment:dv,lights_physical_pars_fragment:fv,lights_fragment_begin:pv,lights_fragment_maps:mv,lights_fragment_end:_v,logdepthbuf_fragment:gv,logdepthbuf_pars_fragment:vv,logdepthbuf_pars_vertex:xv,logdepthbuf_vertex:yv,map_fragment:Ev,map_pars_fragment:Sv,map_particle_fragment:Mv,map_particle_pars_fragment:Tv,metalnessmap_fragment:bv,metalnessmap_pars_fragment:wv,morphinstance_vertex:Av,morphcolor_vertex:Rv,morphnormal_vertex:Cv,morphtarget_pars_vertex:Pv,morphtarget_vertex:Dv,normal_fragment_begin:Lv,normal_fragment_maps:Iv,normal_pars_fragment:Fv,normal_pars_vertex:Uv,normal_vertex:Nv,normalmap_pars_fragment:Ov,clearcoat_normal_fragment_begin:kv,clearcoat_normal_fragment_maps:Bv,clearcoat_pars_fragment:zv,iridescence_pars_fragment:Hv,opaque_fragment:Vv,packing:Gv,premultiplied_alpha_fragment:Wv,project_vertex:Xv,dithering_fragment:jv,dithering_pars_fragment:$v,roughnessmap_fragment:qv,roughnessmap_pars_fragment:Yv,shadowmap_pars_fragment:Kv,shadowmap_pars_vertex:Zv,shadowmap_vertex:Jv,shadowmask_pars_fragment:Qv,skinbase_vertex:e0,skinning_pars_vertex:t0,skinning_vertex:n0,skinnormal_vertex:i0,specularmap_fragment:r0,specularmap_pars_fragment:s0,tonemapping_fragment:a0,tonemapping_pars_fragment:o0,transmission_fragment:c0,transmission_pars_fragment:l0,uv_pars_fragment:u0,uv_pars_vertex:h0,uv_vertex:d0,worldpos_vertex:f0,background_vert:p0,background_frag:m0,backgroundCube_vert:_0,backgroundCube_frag:g0,cube_vert:v0,cube_frag:x0,depth_vert:y0,depth_frag:E0,distanceRGBA_vert:S0,distanceRGBA_frag:M0,equirect_vert:T0,equirect_frag:b0,linedashed_vert:w0,linedashed_frag:A0,meshbasic_vert:R0,meshbasic_frag:C0,meshlambert_vert:P0,meshlambert_frag:D0,meshmatcap_vert:L0,meshmatcap_frag:I0,meshnormal_vert:F0,meshnormal_frag:U0,meshphong_vert:N0,meshphong_frag:O0,meshphysical_vert:k0,meshphysical_frag:B0,meshtoon_vert:z0,meshtoon_frag:H0,points_vert:V0,points_frag:G0,shadow_vert:W0,shadow_frag:X0,sprite_vert:j0,sprite_frag:$0},Ce={common:{diffuse:{value:new ot(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new it},alphaMap:{value:null},alphaMapTransform:{value:new it},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new it}},envmap:{envMap:{value:null},envMapRotation:{value:new it},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new it}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new it}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new it},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new it},normalScale:{value:new et(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new it},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new it}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new it}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new it}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new ot(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMap:{value:[]},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotShadowMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMap:{value:[]},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new ot(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new it},alphaTest:{value:0},uvTransform:{value:new it}},sprite:{diffuse:{value:new ot(16777215)},opacity:{value:1},center:{value:new et(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new it},alphaMap:{value:null},alphaMapTransform:{value:new it},alphaTest:{value:0}}},Cn={basic:{uniforms:nn([Ce.common,Ce.specularmap,Ce.envmap,Ce.aomap,Ce.lightmap,Ce.fog]),vertexShader:at.meshbasic_vert,fragmentShader:at.meshbasic_frag},lambert:{uniforms:nn([Ce.common,Ce.specularmap,Ce.envmap,Ce.aomap,Ce.lightmap,Ce.emissivemap,Ce.bumpmap,Ce.normalmap,Ce.displacementmap,Ce.fog,Ce.lights,{emissive:{value:new ot(0)}}]),vertexShader:at.meshlambert_vert,fragmentShader:at.meshlambert_frag},phong:{uniforms:nn([Ce.common,Ce.specularmap,Ce.envmap,Ce.aomap,Ce.lightmap,Ce.emissivemap,Ce.bumpmap,Ce.normalmap,Ce.displacementmap,Ce.fog,Ce.lights,{emissive:{value:new ot(0)},specular:{value:new ot(1118481)},shininess:{value:30}}]),vertexShader:at.meshphong_vert,fragmentShader:at.meshphong_frag},standard:{uniforms:nn([Ce.common,Ce.envmap,Ce.aomap,Ce.lightmap,Ce.emissivemap,Ce.bumpmap,Ce.normalmap,Ce.displacementmap,Ce.roughnessmap,Ce.metalnessmap,Ce.fog,Ce.lights,{emissive:{value:new ot(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:at.meshphysical_vert,fragmentShader:at.meshphysical_frag},toon:{uniforms:nn([Ce.common,Ce.aomap,Ce.lightmap,Ce.emissivemap,Ce.bumpmap,Ce.normalmap,Ce.displacementmap,Ce.gradientmap,Ce.fog,Ce.lights,{emissive:{value:new ot(0)}}]),vertexShader:at.meshtoon_vert,fragmentShader:at.meshtoon_frag},matcap:{uniforms:nn([Ce.common,Ce.bumpmap,Ce.normalmap,Ce.displacementmap,Ce.fog,{matcap:{value:null}}]),vertexShader:at.meshmatcap_vert,fragmentShader:at.meshmatcap_frag},points:{uniforms:nn([Ce.points,Ce.fog]),vertexShader:at.points_vert,fragmentShader:at.points_frag},dashed:{uniforms:nn([Ce.common,Ce.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:at.linedashed_vert,fragmentShader:at.linedashed_frag},depth:{uniforms:nn([Ce.common,Ce.displacementmap]),vertexShader:at.depth_vert,fragmentShader:at.depth_frag},normal:{uniforms:nn([Ce.common,Ce.bumpmap,Ce.normalmap,Ce.displacementmap,{opacity:{value:1}}]),vertexShader:at.meshnormal_vert,fragmentShader:at.meshnormal_frag},sprite:{uniforms:nn([Ce.sprite,Ce.fog]),vertexShader:at.sprite_vert,fragmentShader:at.sprite_frag},background:{uniforms:{uvTransform:{value:new it},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:at.background_vert,fragmentShader:at.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new it}},vertexShader:at.backgroundCube_vert,fragmentShader:at.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:at.cube_vert,fragmentShader:at.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:at.equirect_vert,fragmentShader:at.equirect_frag},distanceRGBA:{uniforms:nn([Ce.common,Ce.displacementmap,{referencePosition:{value:new X},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:at.distanceRGBA_vert,fragmentShader:at.distanceRGBA_frag},shadow:{uniforms:nn([Ce.lights,Ce.fog,{color:{value:new ot(0)},opacity:{value:1}}]),vertexShader:at.shadow_vert,fragmentShader:at.shadow_frag}};Cn.physical={uniforms:nn([Cn.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new it},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new it},clearcoatNormalScale:{value:new et(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new it},dispersion:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new it},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new it},sheen:{value:0},sheenColor:{value:new ot(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new it},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new it},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new it},transmissionSamplerSize:{value:new et},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new it},attenuationDistance:{value:0},attenuationColor:{value:new ot(0)},specularColor:{value:new ot(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new it},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new it},anisotropyVector:{value:new et},anisotropyMap:{value:null},anisotropyMapTransform:{value:new it}}]),vertexShader:at.meshphysical_vert,fragmentShader:at.meshphysical_frag};const vs={r:0,b:0,g:0},Ei=new Fn,q0=new Ft;function Y0(r,e,t,n,a,o,l){const u=new ot(0);let p=o===!0?0:1,f,_,v=null,x=0,E=null;function R(I){let L=I.isScene===!0?I.background:null;return L&&L.isTexture&&(L=(I.backgroundBlurriness>0?t:e).get(L)),L}function C(I){let L=!1;const B=R(I);B===null?m(u,p):B&&B.isColor&&(m(B,1),L=!0);const D=r.xr.getEnvironmentBlendMode();D==="additive"?n.buffers.color.setClear(0,0,0,1,l):D==="alpha-blend"&&n.buffers.color.setClear(0,0,0,0,l),(r.autoClear||L)&&(n.buffers.depth.setTest(!0),n.buffers.depth.setMask(!0),n.buffers.color.setMask(!0),r.clear(r.autoClearColor,r.autoClearDepth,r.autoClearStencil))}function y(I,L){const B=R(L);B&&(B.isCubeTexture||B.mapping===Fs)?(_===void 0&&(_=new _n(new Di(1,1,1),new ci({name:"BackgroundCubeMaterial",uniforms:sr(Cn.backgroundCube.uniforms),vertexShader:Cn.backgroundCube.vertexShader,fragmentShader:Cn.backgroundCube.fragmentShader,side:an,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),_.geometry.deleteAttribute("normal"),_.geometry.deleteAttribute("uv"),_.onBeforeRender=function(D,H,q){this.matrixWorld.copyPosition(q.matrixWorld)},Object.defineProperty(_.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),a.update(_)),Ei.copy(L.backgroundRotation),Ei.x*=-1,Ei.y*=-1,Ei.z*=-1,B.isCubeTexture&&B.isRenderTargetTexture===!1&&(Ei.y*=-1,Ei.z*=-1),_.material.uniforms.envMap.value=B,_.material.uniforms.flipEnvMap.value=B.isCubeTexture&&B.isRenderTargetTexture===!1?-1:1,_.material.uniforms.backgroundBlurriness.value=L.backgroundBlurriness,_.material.uniforms.backgroundIntensity.value=L.backgroundIntensity,_.material.uniforms.backgroundRotation.value.setFromMatrix4(q0.makeRotationFromEuler(Ei)),_.material.toneMapped=gt.getTransfer(B.colorSpace)!==bt,(v!==B||x!==B.version||E!==r.toneMapping)&&(_.material.needsUpdate=!0,v=B,x=B.version,E=r.toneMapping),_.layers.enableAll(),I.unshift(_,_.geometry,_.material,0,0,null)):B&&B.isTexture&&(f===void 0&&(f=new _n(new Cr(2,2),new ci({name:"BackgroundMaterial",uniforms:sr(Cn.background.uniforms),vertexShader:Cn.background.vertexShader,fragmentShader:Cn.background.fragmentShader,side:oi,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),f.geometry.deleteAttribute("normal"),Object.defineProperty(f.material,"map",{get:function(){return this.uniforms.t2D.value}}),a.update(f)),f.material.uniforms.t2D.value=B,f.material.uniforms.backgroundIntensity.value=L.backgroundIntensity,f.material.toneMapped=gt.getTransfer(B.colorSpace)!==bt,B.matrixAutoUpdate===!0&&B.updateMatrix(),f.material.uniforms.uvTransform.value.copy(B.matrix),(v!==B||x!==B.version||E!==r.toneMapping)&&(f.material.needsUpdate=!0,v=B,x=B.version,E=r.toneMapping),f.layers.enableAll(),I.unshift(f,f.geometry,f.material,0,0,null))}function m(I,L){I.getRGB(vs,hu(r)),n.buffers.color.setClear(vs.r,vs.g,vs.b,L,l)}function N(){_!==void 0&&(_.geometry.dispose(),_.material.dispose(),_=void 0),f!==void 0&&(f.geometry.dispose(),f.material.dispose(),f=void 0)}return{getClearColor:function(){return u},setClearColor:function(I,L=1){u.set(I),p=L,m(u,p)},getClearAlpha:function(){return p},setClearAlpha:function(I){p=I,m(u,p)},render:C,addToRenderList:y,dispose:N}}function K0(r,e){const t=r.getParameter(r.MAX_VERTEX_ATTRIBS),n={},a=x(null);let o=a,l=!1;function u(M,O,te,ee,Z){let he=!1;const ae=v(ee,te,O);o!==ae&&(o=ae,f(o.object)),he=E(M,ee,te,Z),he&&R(M,ee,te,Z),Z!==null&&e.update(Z,r.ELEMENT_ARRAY_BUFFER),(he||l)&&(l=!1,L(M,O,te,ee),Z!==null&&r.bindBuffer(r.ELEMENT_ARRAY_BUFFER,e.get(Z).buffer))}function p(){return r.createVertexArray()}function f(M){return r.bindVertexArray(M)}function _(M){return r.deleteVertexArray(M)}function v(M,O,te){const ee=te.wireframe===!0;let Z=n[M.id];Z===void 0&&(Z={},n[M.id]=Z);let he=Z[O.id];he===void 0&&(he={},Z[O.id]=he);let ae=he[ee];return ae===void 0&&(ae=x(p()),he[ee]=ae),ae}function x(M){const O=[],te=[],ee=[];for(let Z=0;Z<t;Z++)O[Z]=0,te[Z]=0,ee[Z]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:O,enabledAttributes:te,attributeDivisors:ee,object:M,attributes:{},index:null}}function E(M,O,te,ee){const Z=o.attributes,he=O.attributes;let ae=0;const Se=te.getAttributes();for(const re in Se)if(Se[re].location>=0){const De=Z[re];let Ve=he[re];if(Ve===void 0&&(re==="instanceMatrix"&&M.instanceMatrix&&(Ve=M.instanceMatrix),re==="instanceColor"&&M.instanceColor&&(Ve=M.instanceColor)),De===void 0||De.attribute!==Ve||Ve&&De.data!==Ve.data)return!0;ae++}return o.attributesNum!==ae||o.index!==ee}function R(M,O,te,ee){const Z={},he=O.attributes;let ae=0;const Se=te.getAttributes();for(const re in Se)if(Se[re].location>=0){let De=he[re];De===void 0&&(re==="instanceMatrix"&&M.instanceMatrix&&(De=M.instanceMatrix),re==="instanceColor"&&M.instanceColor&&(De=M.instanceColor));const Ve={};Ve.attribute=De,De&&De.data&&(Ve.data=De.data),Z[re]=Ve,ae++}o.attributes=Z,o.attributesNum=ae,o.index=ee}function C(){const M=o.newAttributes;for(let O=0,te=M.length;O<te;O++)M[O]=0}function y(M){m(M,0)}function m(M,O){const te=o.newAttributes,ee=o.enabledAttributes,Z=o.attributeDivisors;te[M]=1,ee[M]===0&&(r.enableVertexAttribArray(M),ee[M]=1),Z[M]!==O&&(r.vertexAttribDivisor(M,O),Z[M]=O)}function N(){const M=o.newAttributes,O=o.enabledAttributes;for(let te=0,ee=O.length;te<ee;te++)O[te]!==M[te]&&(r.disableVertexAttribArray(te),O[te]=0)}function I(M,O,te,ee,Z,he,ae){ae===!0?r.vertexAttribIPointer(M,O,te,Z,he):r.vertexAttribPointer(M,O,te,ee,Z,he)}function L(M,O,te,ee){C();const Z=ee.attributes,he=te.getAttributes(),ae=O.defaultAttributeValues;for(const Se in he){const re=he[Se];if(re.location>=0){let Ae=Z[Se];if(Ae===void 0&&(Se==="instanceMatrix"&&M.instanceMatrix&&(Ae=M.instanceMatrix),Se==="instanceColor"&&M.instanceColor&&(Ae=M.instanceColor)),Ae!==void 0){const De=Ae.normalized,Ve=Ae.itemSize,tt=e.get(Ae);if(tt===void 0)continue;const xt=tt.buffer,Ze=tt.type,ie=tt.bytesPerElement,Te=Ze===r.INT||Ze===r.UNSIGNED_INT||Ae.gpuType===Do;if(Ae.isInterleavedBufferAttribute){const Ee=Ae.data,ue=Ee.stride,ve=Ae.offset;if(Ee.isInstancedInterleavedBuffer){for(let Ye=0;Ye<re.locationSize;Ye++)m(re.location+Ye,Ee.meshPerAttribute);M.isInstancedMesh!==!0&&ee._maxInstanceCount===void 0&&(ee._maxInstanceCount=Ee.meshPerAttribute*Ee.count)}else for(let Ye=0;Ye<re.locationSize;Ye++)y(re.location+Ye);r.bindBuffer(r.ARRAY_BUFFER,xt);for(let Ye=0;Ye<re.locationSize;Ye++)I(re.location+Ye,Ve/re.locationSize,Ze,De,ue*ie,(ve+Ve/re.locationSize*Ye)*ie,Te)}else{if(Ae.isInstancedBufferAttribute){for(let Ee=0;Ee<re.locationSize;Ee++)m(re.location+Ee,Ae.meshPerAttribute);M.isInstancedMesh!==!0&&ee._maxInstanceCount===void 0&&(ee._maxInstanceCount=Ae.meshPerAttribute*Ae.count)}else for(let Ee=0;Ee<re.locationSize;Ee++)y(re.location+Ee);r.bindBuffer(r.ARRAY_BUFFER,xt);for(let Ee=0;Ee<re.locationSize;Ee++)I(re.location+Ee,Ve/re.locationSize,Ze,De,Ve*ie,Ve/re.locationSize*Ee*ie,Te)}}else if(ae!==void 0){const De=ae[Se];if(De!==void 0)switch(De.length){case 2:r.vertexAttrib2fv(re.location,De);break;case 3:r.vertexAttrib3fv(re.location,De);break;case 4:r.vertexAttrib4fv(re.location,De);break;default:r.vertexAttrib1fv(re.location,De)}}}}N()}function B(){q();for(const M in n){const O=n[M];for(const te in O){const ee=O[te];for(const Z in ee)_(ee[Z].object),delete ee[Z];delete O[te]}delete n[M]}}function D(M){if(n[M.id]===void 0)return;const O=n[M.id];for(const te in O){const ee=O[te];for(const Z in ee)_(ee[Z].object),delete ee[Z];delete O[te]}delete n[M.id]}function H(M){for(const O in n){const te=n[O];if(te[M.id]===void 0)continue;const ee=te[M.id];for(const Z in ee)_(ee[Z].object),delete ee[Z];delete te[M.id]}}function q(){P(),l=!0,o!==a&&(o=a,f(o.object))}function P(){a.geometry=null,a.program=null,a.wireframe=!1}return{setup:u,reset:q,resetDefaultState:P,dispose:B,releaseStatesOfGeometry:D,releaseStatesOfProgram:H,initAttributes:C,enableAttribute:y,disableUnusedAttributes:N}}function Z0(r,e,t){let n;function a(f){n=f}function o(f,_){r.drawArrays(n,f,_),t.update(_,n,1)}function l(f,_,v){v!==0&&(r.drawArraysInstanced(n,f,_,v),t.update(_,n,v))}function u(f,_,v){if(v===0)return;e.get("WEBGL_multi_draw").multiDrawArraysWEBGL(n,f,0,_,0,v);let E=0;for(let R=0;R<v;R++)E+=_[R];t.update(E,n,1)}function p(f,_,v,x){if(v===0)return;const E=e.get("WEBGL_multi_draw");if(E===null)for(let R=0;R<f.length;R++)l(f[R],_[R],x[R]);else{E.multiDrawArraysInstancedWEBGL(n,f,0,_,0,x,0,v);let R=0;for(let C=0;C<v;C++)R+=_[C]*x[C];t.update(R,n,1)}}this.setMode=a,this.render=o,this.renderInstances=l,this.renderMultiDraw=u,this.renderMultiDrawInstances=p}function J0(r,e,t,n){let a;function o(){if(a!==void 0)return a;if(e.has("EXT_texture_filter_anisotropic")===!0){const H=e.get("EXT_texture_filter_anisotropic");a=r.getParameter(H.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else a=0;return a}function l(H){return!(H!==Mn&&n.convert(H)!==r.getParameter(r.IMPLEMENTATION_COLOR_READ_FORMAT))}function u(H){const q=H===wr&&(e.has("EXT_color_buffer_half_float")||e.has("EXT_color_buffer_float"));return!(H!==In&&n.convert(H)!==r.getParameter(r.IMPLEMENTATION_COLOR_READ_TYPE)&&H!==jn&&!q)}function p(H){if(H==="highp"){if(r.getShaderPrecisionFormat(r.VERTEX_SHADER,r.HIGH_FLOAT).precision>0&&r.getShaderPrecisionFormat(r.FRAGMENT_SHADER,r.HIGH_FLOAT).precision>0)return"highp";H="mediump"}return H==="mediump"&&r.getShaderPrecisionFormat(r.VERTEX_SHADER,r.MEDIUM_FLOAT).precision>0&&r.getShaderPrecisionFormat(r.FRAGMENT_SHADER,r.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let f=t.precision!==void 0?t.precision:"highp";const _=p(f);_!==f&&(console.warn("THREE.WebGLRenderer:",f,"not supported, using",_,"instead."),f=_);const v=t.logarithmicDepthBuffer===!0,x=t.reversedDepthBuffer===!0&&e.has("EXT_clip_control"),E=r.getParameter(r.MAX_TEXTURE_IMAGE_UNITS),R=r.getParameter(r.MAX_VERTEX_TEXTURE_IMAGE_UNITS),C=r.getParameter(r.MAX_TEXTURE_SIZE),y=r.getParameter(r.MAX_CUBE_MAP_TEXTURE_SIZE),m=r.getParameter(r.MAX_VERTEX_ATTRIBS),N=r.getParameter(r.MAX_VERTEX_UNIFORM_VECTORS),I=r.getParameter(r.MAX_VARYING_VECTORS),L=r.getParameter(r.MAX_FRAGMENT_UNIFORM_VECTORS),B=R>0,D=r.getParameter(r.MAX_SAMPLES);return{isWebGL2:!0,getMaxAnisotropy:o,getMaxPrecision:p,textureFormatReadable:l,textureTypeReadable:u,precision:f,logarithmicDepthBuffer:v,reversedDepthBuffer:x,maxTextures:E,maxVertexTextures:R,maxTextureSize:C,maxCubemapSize:y,maxAttributes:m,maxVertexUniforms:N,maxVaryings:I,maxFragmentUniforms:L,vertexTextures:B,maxSamples:D}}function Q0(r){const e=this;let t=null,n=0,a=!1,o=!1;const l=new ti,u=new it,p={value:null,needsUpdate:!1};this.uniform=p,this.numPlanes=0,this.numIntersection=0,this.init=function(v,x){const E=v.length!==0||x||n!==0||a;return a=x,n=v.length,E},this.beginShadows=function(){o=!0,_(null)},this.endShadows=function(){o=!1},this.setGlobalState=function(v,x){t=_(v,x,0)},this.setState=function(v,x,E){const R=v.clippingPlanes,C=v.clipIntersection,y=v.clipShadows,m=r.get(v);if(!a||R===null||R.length===0||o&&!y)o?_(null):f();else{const N=o?0:n,I=N*4;let L=m.clippingState||null;p.value=L,L=_(R,x,I,E);for(let B=0;B!==I;++B)L[B]=t[B];m.clippingState=L,this.numIntersection=C?this.numPlanes:0,this.numPlanes+=N}};function f(){p.value!==t&&(p.value=t,p.needsUpdate=n>0),e.numPlanes=n,e.numIntersection=0}function _(v,x,E,R){const C=v!==null?v.length:0;let y=null;if(C!==0){if(y=p.value,R!==!0||y===null){const m=E+C*4,N=x.matrixWorldInverse;u.getNormalMatrix(N),(y===null||y.length<m)&&(y=new Float32Array(m));for(let I=0,L=E;I!==C;++I,L+=4)l.copy(v[I]).applyMatrix4(N,u),l.normal.toArray(y,L),y[L+3]=l.constant}p.value=y,p.needsUpdate=!0}return e.numPlanes=C,e.numIntersection=0,y}}function ex(r){let e=new WeakMap;function t(l,u){return u===Ka?l.mapping=nr:u===Za&&(l.mapping=ir),l}function n(l){if(l&&l.isTexture){const u=l.mapping;if(u===Ka||u===Za)if(e.has(l)){const p=e.get(l).texture;return t(p,l.mapping)}else{const p=l.image;if(p&&p.height>0){const f=new K_(p.height);return f.fromEquirectangularTexture(r,l),e.set(l,f),l.addEventListener("dispose",a),t(f.texture,l.mapping)}else return null}}return l}function a(l){const u=l.target;u.removeEventListener("dispose",a);const p=e.get(u);p!==void 0&&(e.delete(u),p.dispose())}function o(){e=new WeakMap}return{get:n,dispose:o}}const Ki=4,vl=[.125,.215,.35,.446,.526,.582],bi=20,Da=new gu,xl=new ot;let La=null,Ia=0,Fa=0,Ua=!1;const Mi=(1+Math.sqrt(5))/2,$i=1/Mi,yl=[new X(-Mi,$i,0),new X(Mi,$i,0),new X(-$i,0,Mi),new X($i,0,Mi),new X(0,Mi,-$i),new X(0,Mi,$i),new X(-1,1,-1),new X(1,1,-1),new X(-1,1,1),new X(1,1,1)],tx=new X;class El{constructor(e){this._renderer=e,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._lodPlanes=[],this._sizeLods=[],this._sigmas=[],this._blurMaterial=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._compileMaterial(this._blurMaterial)}fromScene(e,t=0,n=.1,a=100,o={}){const{size:l=256,position:u=tx}=o;La=this._renderer.getRenderTarget(),Ia=this._renderer.getActiveCubeFace(),Fa=this._renderer.getActiveMipmapLevel(),Ua=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(l);const p=this._allocateTargets();return p.depthBuffer=!0,this._sceneToCubeUV(e,n,a,p,u),t>0&&this._blur(p,0,0,t),this._applyPMREM(p),this._cleanup(p),p}fromEquirectangular(e,t=null){return this._fromTexture(e,t)}fromCubemap(e,t=null){return this._fromTexture(e,t)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=Tl(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=Ml(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose()}_setSize(e){this._lodMax=Math.floor(Math.log2(e)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let e=0;e<this._lodPlanes.length;e++)this._lodPlanes[e].dispose()}_cleanup(e){this._renderer.setRenderTarget(La,Ia,Fa),this._renderer.xr.enabled=Ua,e.scissorTest=!1,xs(e,0,0,e.width,e.height)}_fromTexture(e,t){e.mapping===nr||e.mapping===ir?this._setSize(e.image.length===0?16:e.image[0].width||e.image[0].image.width):this._setSize(e.image.width/4),La=this._renderer.getRenderTarget(),Ia=this._renderer.getActiveCubeFace(),Fa=this._renderer.getActiveMipmapLevel(),Ua=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;const n=t||this._allocateTargets();return this._textureToCubeUV(e,n),this._applyPMREM(n),this._cleanup(n),n}_allocateTargets(){const e=3*Math.max(this._cubeSize,112),t=4*this._cubeSize,n={magFilter:Pn,minFilter:Pn,generateMipmaps:!1,type:wr,format:Mn,colorSpace:rr,depthBuffer:!1},a=Sl(e,t,n);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==e||this._pingPongRenderTarget.height!==t){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=Sl(e,t,n);const{_lodMax:o}=this;({sizeLods:this._sizeLods,lodPlanes:this._lodPlanes,sigmas:this._sigmas}=nx(o)),this._blurMaterial=ix(o,e,t)}return a}_compileMaterial(e){const t=new _n(this._lodPlanes[0],e);this._renderer.compile(t,Da)}_sceneToCubeUV(e,t,n,a,o){const p=new mn(90,1,t,n),f=[1,-1,1,1,1,1],_=[1,1,1,-1,-1,-1],v=this._renderer,x=v.autoClear,E=v.toneMapping;v.getClearColor(xl),v.toneMapping=ai,v.autoClear=!1,v.state.buffers.depth.getReversed()&&(v.setRenderTarget(a),v.clearDepth(),v.setRenderTarget(null));const C=new Bo({name:"PMREM.Background",side:an,depthWrite:!1,depthTest:!1}),y=new _n(new Di,C);let m=!1;const N=e.background;N?N.isColor&&(C.color.copy(N),e.background=null,m=!0):(C.color.copy(xl),m=!0);for(let I=0;I<6;I++){const L=I%3;L===0?(p.up.set(0,f[I],0),p.position.set(o.x,o.y,o.z),p.lookAt(o.x+_[I],o.y,o.z)):L===1?(p.up.set(0,0,f[I]),p.position.set(o.x,o.y,o.z),p.lookAt(o.x,o.y+_[I],o.z)):(p.up.set(0,f[I],0),p.position.set(o.x,o.y,o.z),p.lookAt(o.x,o.y,o.z+_[I]));const B=this._cubeSize;xs(a,L*B,I>2?B:0,B,B),v.setRenderTarget(a),m&&v.render(y,p),v.render(e,p)}y.geometry.dispose(),y.material.dispose(),v.toneMapping=E,v.autoClear=x,e.background=N}_textureToCubeUV(e,t){const n=this._renderer,a=e.mapping===nr||e.mapping===ir;a?(this._cubemapMaterial===null&&(this._cubemapMaterial=Tl()),this._cubemapMaterial.uniforms.flipEnvMap.value=e.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=Ml());const o=a?this._cubemapMaterial:this._equirectMaterial,l=new _n(this._lodPlanes[0],o),u=o.uniforms;u.envMap.value=e;const p=this._cubeSize;xs(t,0,0,3*p,2*p),n.setRenderTarget(t),n.render(l,Da)}_applyPMREM(e){const t=this._renderer,n=t.autoClear;t.autoClear=!1;const a=this._lodPlanes.length;for(let o=1;o<a;o++){const l=Math.sqrt(this._sigmas[o]*this._sigmas[o]-this._sigmas[o-1]*this._sigmas[o-1]),u=yl[(a-o-1)%yl.length];this._blur(e,o-1,o,l,u)}t.autoClear=n}_blur(e,t,n,a,o){const l=this._pingPongRenderTarget;this._halfBlur(e,l,t,n,a,"latitudinal",o),this._halfBlur(l,e,n,n,a,"longitudinal",o)}_halfBlur(e,t,n,a,o,l,u){const p=this._renderer,f=this._blurMaterial;l!=="latitudinal"&&l!=="longitudinal"&&console.error("blur direction must be either latitudinal or longitudinal!");const _=3,v=new _n(this._lodPlanes[a],f),x=f.uniforms,E=this._sizeLods[n]-1,R=isFinite(o)?Math.PI/(2*E):2*Math.PI/(2*bi-1),C=o/R,y=isFinite(o)?1+Math.floor(_*C):bi;y>bi&&console.warn(`sigmaRadians, ${o}, is too large and will clip, as it requested ${y} samples when the maximum is set to ${bi}`);const m=[];let N=0;for(let H=0;H<bi;++H){const q=H/C,P=Math.exp(-q*q/2);m.push(P),H===0?N+=P:H<y&&(N+=2*P)}for(let H=0;H<m.length;H++)m[H]=m[H]/N;x.envMap.value=e.texture,x.samples.value=y,x.weights.value=m,x.latitudinal.value=l==="latitudinal",u&&(x.poleAxis.value=u);const{_lodMax:I}=this;x.dTheta.value=R,x.mipInt.value=I-n;const L=this._sizeLods[a],B=3*L*(a>I-Ki?a-I+Ki:0),D=4*(this._cubeSize-L);xs(t,B,D,3*L,2*L),p.setRenderTarget(t),p.render(v,Da)}}function nx(r){const e=[],t=[],n=[];let a=r;const o=r-Ki+1+vl.length;for(let l=0;l<o;l++){const u=Math.pow(2,a);t.push(u);let p=1/u;l>r-Ki?p=vl[l-r+Ki-1]:l===0&&(p=0),n.push(p);const f=1/(u-2),_=-f,v=1+f,x=[_,_,v,_,v,v,_,_,v,v,_,v],E=6,R=6,C=3,y=2,m=1,N=new Float32Array(C*R*E),I=new Float32Array(y*R*E),L=new Float32Array(m*R*E);for(let D=0;D<E;D++){const H=D%3*2/3-1,q=D>2?0:-1,P=[H,q,0,H+2/3,q,0,H+2/3,q+1,0,H,q,0,H+2/3,q+1,0,H,q+1,0];N.set(P,C*R*D),I.set(x,y*R*D);const M=[D,D,D,D,D,D];L.set(M,m*R*D)}const B=new cn;B.setAttribute("position",new Ln(N,C)),B.setAttribute("uv",new Ln(I,y)),B.setAttribute("faceIndex",new Ln(L,m)),e.push(B),a>Ki&&a--}return{lodPlanes:e,sizeLods:t,sigmas:n}}function Sl(r,e,t){const n=new Pi(r,e,t);return n.texture.mapping=Fs,n.texture.name="PMREM.cubeUv",n.scissorTest=!0,n}function xs(r,e,t,n,a){r.viewport.set(e,t,n,a),r.scissor.set(e,t,n,a)}function ix(r,e,t){const n=new Float32Array(bi),a=new X(0,1,0);return new ci({name:"SphericalGaussianBlur",defines:{n:bi,CUBEUV_TEXEL_WIDTH:1/e,CUBEUV_TEXEL_HEIGHT:1/t,CUBEUV_MAX_MIP:`${r}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:n},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:a}},vertexShader:Xo(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`,blending:si,depthTest:!1,depthWrite:!1})}function Ml(){return new ci({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:Xo(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:si,depthTest:!1,depthWrite:!1})}function Tl(){return new ci({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:Xo(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:si,depthTest:!1,depthWrite:!1})}function Xo(){return`

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`}function rx(r){let e=new WeakMap,t=null;function n(u){if(u&&u.isTexture){const p=u.mapping,f=p===Ka||p===Za,_=p===nr||p===ir;if(f||_){let v=e.get(u);const x=v!==void 0?v.texture.pmremVersion:0;if(u.isRenderTargetTexture&&u.pmremVersion!==x)return t===null&&(t=new El(r)),v=f?t.fromEquirectangular(u,v):t.fromCubemap(u,v),v.texture.pmremVersion=u.pmremVersion,e.set(u,v),v.texture;if(v!==void 0)return v.texture;{const E=u.image;return f&&E&&E.height>0||_&&E&&a(E)?(t===null&&(t=new El(r)),v=f?t.fromEquirectangular(u):t.fromCubemap(u),v.texture.pmremVersion=u.pmremVersion,e.set(u,v),u.addEventListener("dispose",o),v.texture):null}}}return u}function a(u){let p=0;const f=6;for(let _=0;_<f;_++)u[_]!==void 0&&p++;return p===f}function o(u){const p=u.target;p.removeEventListener("dispose",o);const f=e.get(p);f!==void 0&&(e.delete(p),f.dispose())}function l(){e=new WeakMap,t!==null&&(t.dispose(),t=null)}return{get:n,dispose:l}}function sx(r){const e={};function t(n){if(e[n]!==void 0)return e[n];let a;switch(n){case"WEBGL_depth_texture":a=r.getExtension("WEBGL_depth_texture")||r.getExtension("MOZ_WEBGL_depth_texture")||r.getExtension("WEBKIT_WEBGL_depth_texture");break;case"EXT_texture_filter_anisotropic":a=r.getExtension("EXT_texture_filter_anisotropic")||r.getExtension("MOZ_EXT_texture_filter_anisotropic")||r.getExtension("WEBKIT_EXT_texture_filter_anisotropic");break;case"WEBGL_compressed_texture_s3tc":a=r.getExtension("WEBGL_compressed_texture_s3tc")||r.getExtension("MOZ_WEBGL_compressed_texture_s3tc")||r.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");break;case"WEBGL_compressed_texture_pvrtc":a=r.getExtension("WEBGL_compressed_texture_pvrtc")||r.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");break;default:a=r.getExtension(n)}return e[n]=a,a}return{has:function(n){return t(n)!==null},init:function(){t("EXT_color_buffer_float"),t("WEBGL_clip_cull_distance"),t("OES_texture_float_linear"),t("EXT_color_buffer_half_float"),t("WEBGL_multisampled_render_to_texture"),t("WEBGL_render_shared_exponent")},get:function(n){const a=t(n);return a===null&&Qi("THREE.WebGLRenderer: "+n+" extension not supported."),a}}}function ax(r,e,t,n){const a={},o=new WeakMap;function l(v){const x=v.target;x.index!==null&&e.remove(x.index);for(const R in x.attributes)e.remove(x.attributes[R]);x.removeEventListener("dispose",l),delete a[x.id];const E=o.get(x);E&&(e.remove(E),o.delete(x)),n.releaseStatesOfGeometry(x),x.isInstancedBufferGeometry===!0&&delete x._maxInstanceCount,t.memory.geometries--}function u(v,x){return a[x.id]===!0||(x.addEventListener("dispose",l),a[x.id]=!0,t.memory.geometries++),x}function p(v){const x=v.attributes;for(const E in x)e.update(x[E],r.ARRAY_BUFFER)}function f(v){const x=[],E=v.index,R=v.attributes.position;let C=0;if(E!==null){const N=E.array;C=E.version;for(let I=0,L=N.length;I<L;I+=3){const B=N[I+0],D=N[I+1],H=N[I+2];x.push(B,D,D,H,H,B)}}else if(R!==void 0){const N=R.array;C=R.version;for(let I=0,L=N.length/3-1;I<L;I+=3){const B=I+0,D=I+1,H=I+2;x.push(B,D,D,H,H,B)}}else return;const y=new(au(x)?uu:lu)(x,1);y.version=C;const m=o.get(v);m&&e.remove(m),o.set(v,y)}function _(v){const x=o.get(v);if(x){const E=v.index;E!==null&&x.version<E.version&&f(v)}else f(v);return o.get(v)}return{get:u,update:p,getWireframeAttribute:_}}function ox(r,e,t){let n;function a(x){n=x}let o,l;function u(x){o=x.type,l=x.bytesPerElement}function p(x,E){r.drawElements(n,E,o,x*l),t.update(E,n,1)}function f(x,E,R){R!==0&&(r.drawElementsInstanced(n,E,o,x*l,R),t.update(E,n,R))}function _(x,E,R){if(R===0)return;e.get("WEBGL_multi_draw").multiDrawElementsWEBGL(n,E,0,o,x,0,R);let y=0;for(let m=0;m<R;m++)y+=E[m];t.update(y,n,1)}function v(x,E,R,C){if(R===0)return;const y=e.get("WEBGL_multi_draw");if(y===null)for(let m=0;m<x.length;m++)f(x[m]/l,E[m],C[m]);else{y.multiDrawElementsInstancedWEBGL(n,E,0,o,x,0,C,0,R);let m=0;for(let N=0;N<R;N++)m+=E[N]*C[N];t.update(m,n,1)}}this.setMode=a,this.setIndex=u,this.render=p,this.renderInstances=f,this.renderMultiDraw=_,this.renderMultiDrawInstances=v}function cx(r){const e={geometries:0,textures:0},t={frame:0,calls:0,triangles:0,points:0,lines:0};function n(o,l,u){switch(t.calls++,l){case r.TRIANGLES:t.triangles+=u*(o/3);break;case r.LINES:t.lines+=u*(o/2);break;case r.LINE_STRIP:t.lines+=u*(o-1);break;case r.LINE_LOOP:t.lines+=u*o;break;case r.POINTS:t.points+=u*o;break;default:console.error("THREE.WebGLInfo: Unknown draw mode:",l);break}}function a(){t.calls=0,t.triangles=0,t.points=0,t.lines=0}return{memory:e,render:t,programs:null,autoReset:!0,reset:a,update:n}}function lx(r,e,t){const n=new WeakMap,a=new Ut;function o(l,u,p){const f=l.morphTargetInfluences,_=u.morphAttributes.position||u.morphAttributes.normal||u.morphAttributes.color,v=_!==void 0?_.length:0;let x=n.get(u);if(x===void 0||x.count!==v){let P=function(){H.dispose(),n.delete(u),u.removeEventListener("dispose",P)};x!==void 0&&x.texture.dispose();const E=u.morphAttributes.position!==void 0,R=u.morphAttributes.normal!==void 0,C=u.morphAttributes.color!==void 0,y=u.morphAttributes.position||[],m=u.morphAttributes.normal||[],N=u.morphAttributes.color||[];let I=0;E===!0&&(I=1),R===!0&&(I=2),C===!0&&(I=3);let L=u.attributes.position.count*I,B=1;L>e.maxTextureSize&&(B=Math.ceil(L/e.maxTextureSize),L=e.maxTextureSize);const D=new Float32Array(L*B*4*v),H=new ou(D,L,B,v);H.type=jn,H.needsUpdate=!0;const q=I*4;for(let M=0;M<v;M++){const O=y[M],te=m[M],ee=N[M],Z=L*B*4*M;for(let he=0;he<O.count;he++){const ae=he*q;E===!0&&(a.fromBufferAttribute(O,he),D[Z+ae+0]=a.x,D[Z+ae+1]=a.y,D[Z+ae+2]=a.z,D[Z+ae+3]=0),R===!0&&(a.fromBufferAttribute(te,he),D[Z+ae+4]=a.x,D[Z+ae+5]=a.y,D[Z+ae+6]=a.z,D[Z+ae+7]=0),C===!0&&(a.fromBufferAttribute(ee,he),D[Z+ae+8]=a.x,D[Z+ae+9]=a.y,D[Z+ae+10]=a.z,D[Z+ae+11]=ee.itemSize===4?a.w:1)}}x={count:v,texture:H,size:new et(L,B)},n.set(u,x),u.addEventListener("dispose",P)}if(l.isInstancedMesh===!0&&l.morphTexture!==null)p.getUniforms().setValue(r,"morphTexture",l.morphTexture,t);else{let E=0;for(let C=0;C<f.length;C++)E+=f[C];const R=u.morphTargetsRelative?1:1-E;p.getUniforms().setValue(r,"morphTargetBaseInfluence",R),p.getUniforms().setValue(r,"morphTargetInfluences",f)}p.getUniforms().setValue(r,"morphTargetsTexture",x.texture,t),p.getUniforms().setValue(r,"morphTargetsTextureSize",x.size)}return{update:o}}function ux(r,e,t,n){let a=new WeakMap;function o(p){const f=n.render.frame,_=p.geometry,v=e.get(p,_);if(a.get(v)!==f&&(e.update(v),a.set(v,f)),p.isInstancedMesh&&(p.hasEventListener("dispose",u)===!1&&p.addEventListener("dispose",u),a.get(p)!==f&&(t.update(p.instanceMatrix,r.ARRAY_BUFFER),p.instanceColor!==null&&t.update(p.instanceColor,r.ARRAY_BUFFER),a.set(p,f))),p.isSkinnedMesh){const x=p.skeleton;a.get(x)!==f&&(x.update(),a.set(x,f))}return v}function l(){a=new WeakMap}function u(p){const f=p.target;f.removeEventListener("dispose",u),t.remove(f.instanceMatrix),f.instanceColor!==null&&t.remove(f.instanceColor)}return{update:o,dispose:l}}const xu=new on,bl=new mu(1,1),yu=new ou,Eu=new I_,Su=new fu,wl=[],Al=[],Rl=new Float32Array(16),Cl=new Float32Array(9),Pl=new Float32Array(4);function or(r,e,t){const n=r[0];if(n<=0||n>0)return r;const a=e*t;let o=wl[a];if(o===void 0&&(o=new Float32Array(a),wl[a]=o),e!==0){n.toArray(o,0);for(let l=1,u=0;l!==e;++l)u+=t,r[l].toArray(o,u)}return o}function Xt(r,e){if(r.length!==e.length)return!1;for(let t=0,n=r.length;t<n;t++)if(r[t]!==e[t])return!1;return!0}function jt(r,e){for(let t=0,n=e.length;t<n;t++)r[t]=e[t]}function ks(r,e){let t=Al[e];t===void 0&&(t=new Int32Array(e),Al[e]=t);for(let n=0;n!==e;++n)t[n]=r.allocateTextureUnit();return t}function hx(r,e){const t=this.cache;t[0]!==e&&(r.uniform1f(this.addr,e),t[0]=e)}function dx(r,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(r.uniform2f(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Xt(t,e))return;r.uniform2fv(this.addr,e),jt(t,e)}}function fx(r,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(r.uniform3f(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else if(e.r!==void 0)(t[0]!==e.r||t[1]!==e.g||t[2]!==e.b)&&(r.uniform3f(this.addr,e.r,e.g,e.b),t[0]=e.r,t[1]=e.g,t[2]=e.b);else{if(Xt(t,e))return;r.uniform3fv(this.addr,e),jt(t,e)}}function px(r,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(r.uniform4f(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Xt(t,e))return;r.uniform4fv(this.addr,e),jt(t,e)}}function mx(r,e){const t=this.cache,n=e.elements;if(n===void 0){if(Xt(t,e))return;r.uniformMatrix2fv(this.addr,!1,e),jt(t,e)}else{if(Xt(t,n))return;Pl.set(n),r.uniformMatrix2fv(this.addr,!1,Pl),jt(t,n)}}function _x(r,e){const t=this.cache,n=e.elements;if(n===void 0){if(Xt(t,e))return;r.uniformMatrix3fv(this.addr,!1,e),jt(t,e)}else{if(Xt(t,n))return;Cl.set(n),r.uniformMatrix3fv(this.addr,!1,Cl),jt(t,n)}}function gx(r,e){const t=this.cache,n=e.elements;if(n===void 0){if(Xt(t,e))return;r.uniformMatrix4fv(this.addr,!1,e),jt(t,e)}else{if(Xt(t,n))return;Rl.set(n),r.uniformMatrix4fv(this.addr,!1,Rl),jt(t,n)}}function vx(r,e){const t=this.cache;t[0]!==e&&(r.uniform1i(this.addr,e),t[0]=e)}function xx(r,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(r.uniform2i(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Xt(t,e))return;r.uniform2iv(this.addr,e),jt(t,e)}}function yx(r,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(r.uniform3i(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(Xt(t,e))return;r.uniform3iv(this.addr,e),jt(t,e)}}function Ex(r,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(r.uniform4i(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Xt(t,e))return;r.uniform4iv(this.addr,e),jt(t,e)}}function Sx(r,e){const t=this.cache;t[0]!==e&&(r.uniform1ui(this.addr,e),t[0]=e)}function Mx(r,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(r.uniform2ui(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Xt(t,e))return;r.uniform2uiv(this.addr,e),jt(t,e)}}function Tx(r,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(r.uniform3ui(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(Xt(t,e))return;r.uniform3uiv(this.addr,e),jt(t,e)}}function bx(r,e){const t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(r.uniform4ui(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Xt(t,e))return;r.uniform4uiv(this.addr,e),jt(t,e)}}function wx(r,e,t){const n=this.cache,a=t.allocateTextureUnit();n[0]!==a&&(r.uniform1i(this.addr,a),n[0]=a);let o;this.type===r.SAMPLER_2D_SHADOW?(bl.compareFunction=su,o=bl):o=xu,t.setTexture2D(e||o,a)}function Ax(r,e,t){const n=this.cache,a=t.allocateTextureUnit();n[0]!==a&&(r.uniform1i(this.addr,a),n[0]=a),t.setTexture3D(e||Eu,a)}function Rx(r,e,t){const n=this.cache,a=t.allocateTextureUnit();n[0]!==a&&(r.uniform1i(this.addr,a),n[0]=a),t.setTextureCube(e||Su,a)}function Cx(r,e,t){const n=this.cache,a=t.allocateTextureUnit();n[0]!==a&&(r.uniform1i(this.addr,a),n[0]=a),t.setTexture2DArray(e||yu,a)}function Px(r){switch(r){case 5126:return hx;case 35664:return dx;case 35665:return fx;case 35666:return px;case 35674:return mx;case 35675:return _x;case 35676:return gx;case 5124:case 35670:return vx;case 35667:case 35671:return xx;case 35668:case 35672:return yx;case 35669:case 35673:return Ex;case 5125:return Sx;case 36294:return Mx;case 36295:return Tx;case 36296:return bx;case 35678:case 36198:case 36298:case 36306:case 35682:return wx;case 35679:case 36299:case 36307:return Ax;case 35680:case 36300:case 36308:case 36293:return Rx;case 36289:case 36303:case 36311:case 36292:return Cx}}function Dx(r,e){r.uniform1fv(this.addr,e)}function Lx(r,e){const t=or(e,this.size,2);r.uniform2fv(this.addr,t)}function Ix(r,e){const t=or(e,this.size,3);r.uniform3fv(this.addr,t)}function Fx(r,e){const t=or(e,this.size,4);r.uniform4fv(this.addr,t)}function Ux(r,e){const t=or(e,this.size,4);r.uniformMatrix2fv(this.addr,!1,t)}function Nx(r,e){const t=or(e,this.size,9);r.uniformMatrix3fv(this.addr,!1,t)}function Ox(r,e){const t=or(e,this.size,16);r.uniformMatrix4fv(this.addr,!1,t)}function kx(r,e){r.uniform1iv(this.addr,e)}function Bx(r,e){r.uniform2iv(this.addr,e)}function zx(r,e){r.uniform3iv(this.addr,e)}function Hx(r,e){r.uniform4iv(this.addr,e)}function Vx(r,e){r.uniform1uiv(this.addr,e)}function Gx(r,e){r.uniform2uiv(this.addr,e)}function Wx(r,e){r.uniform3uiv(this.addr,e)}function Xx(r,e){r.uniform4uiv(this.addr,e)}function jx(r,e,t){const n=this.cache,a=e.length,o=ks(t,a);Xt(n,o)||(r.uniform1iv(this.addr,o),jt(n,o));for(let l=0;l!==a;++l)t.setTexture2D(e[l]||xu,o[l])}function $x(r,e,t){const n=this.cache,a=e.length,o=ks(t,a);Xt(n,o)||(r.uniform1iv(this.addr,o),jt(n,o));for(let l=0;l!==a;++l)t.setTexture3D(e[l]||Eu,o[l])}function qx(r,e,t){const n=this.cache,a=e.length,o=ks(t,a);Xt(n,o)||(r.uniform1iv(this.addr,o),jt(n,o));for(let l=0;l!==a;++l)t.setTextureCube(e[l]||Su,o[l])}function Yx(r,e,t){const n=this.cache,a=e.length,o=ks(t,a);Xt(n,o)||(r.uniform1iv(this.addr,o),jt(n,o));for(let l=0;l!==a;++l)t.setTexture2DArray(e[l]||yu,o[l])}function Kx(r){switch(r){case 5126:return Dx;case 35664:return Lx;case 35665:return Ix;case 35666:return Fx;case 35674:return Ux;case 35675:return Nx;case 35676:return Ox;case 5124:case 35670:return kx;case 35667:case 35671:return Bx;case 35668:case 35672:return zx;case 35669:case 35673:return Hx;case 5125:return Vx;case 36294:return Gx;case 36295:return Wx;case 36296:return Xx;case 35678:case 36198:case 36298:case 36306:case 35682:return jx;case 35679:case 36299:case 36307:return $x;case 35680:case 36300:case 36308:case 36293:return qx;case 36289:case 36303:case 36311:case 36292:return Yx}}class Zx{constructor(e,t,n){this.id=e,this.addr=n,this.cache=[],this.type=t.type,this.setValue=Px(t.type)}}class Jx{constructor(e,t,n){this.id=e,this.addr=n,this.cache=[],this.type=t.type,this.size=t.size,this.setValue=Kx(t.type)}}class Qx{constructor(e){this.id=e,this.seq=[],this.map={}}setValue(e,t,n){const a=this.seq;for(let o=0,l=a.length;o!==l;++o){const u=a[o];u.setValue(e,t[u.id],n)}}}const Na=/(\w+)(\])?(\[|\.)?/g;function Dl(r,e){r.seq.push(e),r.map[e.id]=e}function ey(r,e,t){const n=r.name,a=n.length;for(Na.lastIndex=0;;){const o=Na.exec(n),l=Na.lastIndex;let u=o[1];const p=o[2]==="]",f=o[3];if(p&&(u=u|0),f===void 0||f==="["&&l+2===a){Dl(t,f===void 0?new Zx(u,r,e):new Jx(u,r,e));break}else{let v=t.map[u];v===void 0&&(v=new Qx(u),Dl(t,v)),t=v}}}class Rs{constructor(e,t){this.seq=[],this.map={};const n=e.getProgramParameter(t,e.ACTIVE_UNIFORMS);for(let a=0;a<n;++a){const o=e.getActiveUniform(t,a),l=e.getUniformLocation(t,o.name);ey(o,l,this)}}setValue(e,t,n,a){const o=this.map[t];o!==void 0&&o.setValue(e,n,a)}setOptional(e,t,n){const a=t[n];a!==void 0&&this.setValue(e,n,a)}static upload(e,t,n,a){for(let o=0,l=t.length;o!==l;++o){const u=t[o],p=n[u.id];p.needsUpdate!==!1&&u.setValue(e,p.value,a)}}static seqWithValue(e,t){const n=[];for(let a=0,o=e.length;a!==o;++a){const l=e[a];l.id in t&&n.push(l)}return n}}function Ll(r,e,t){const n=r.createShader(e);return r.shaderSource(n,t),r.compileShader(n),n}const ty=37297;let ny=0;function iy(r,e){const t=r.split(`
`),n=[],a=Math.max(e-6,0),o=Math.min(e+6,t.length);for(let l=a;l<o;l++){const u=l+1;n.push(`${u===e?">":" "} ${u}: ${t[l]}`)}return n.join(`
`)}const Il=new it;function ry(r){gt._getMatrix(Il,gt.workingColorSpace,r);const e=`mat3( ${Il.elements.map(t=>t.toFixed(4))} )`;switch(gt.getTransfer(r)){case Cs:return[e,"LinearTransferOETF"];case bt:return[e,"sRGBTransferOETF"];default:return console.warn("THREE.WebGLProgram: Unsupported color space: ",r),[e,"LinearTransferOETF"]}}function Fl(r,e,t){const n=r.getShaderParameter(e,r.COMPILE_STATUS),o=(r.getShaderInfoLog(e)||"").trim();if(n&&o==="")return"";const l=/ERROR: 0:(\d+)/.exec(o);if(l){const u=parseInt(l[1]);return t.toUpperCase()+`

`+o+`

`+iy(r.getShaderSource(e),u)}else return o}function sy(r,e){const t=ry(e);return[`vec4 ${r}( vec4 value ) {`,`	return ${t[1]}( vec4( value.rgb * ${t[0]}, value.a ) );`,"}"].join(`
`)}function ay(r,e){let t;switch(e){case o_:t="Linear";break;case c_:t="Reinhard";break;case l_:t="Cineon";break;case ql:t="ACESFilmic";break;case h_:t="AgX";break;case d_:t="Neutral";break;case u_:t="Custom";break;default:console.warn("THREE.WebGLProgram: Unsupported toneMapping:",e),t="Linear"}return"vec3 "+r+"( vec3 color ) { return "+t+"ToneMapping( color ); }"}const ys=new X;function oy(){gt.getLuminanceCoefficients(ys);const r=ys.x.toFixed(4),e=ys.y.toFixed(4),t=ys.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${r}, ${e}, ${t} );`,"	return dot( weights, rgb );","}"].join(`
`)}function cy(r){return[r.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",r.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(yr).join(`
`)}function ly(r){const e=[];for(const t in r){const n=r[t];n!==!1&&e.push("#define "+t+" "+n)}return e.join(`
`)}function uy(r,e){const t={},n=r.getProgramParameter(e,r.ACTIVE_ATTRIBUTES);for(let a=0;a<n;a++){const o=r.getActiveAttrib(e,a),l=o.name;let u=1;o.type===r.FLOAT_MAT2&&(u=2),o.type===r.FLOAT_MAT3&&(u=3),o.type===r.FLOAT_MAT4&&(u=4),t[l]={type:o.type,location:r.getAttribLocation(e,l),locationSize:u}}return t}function yr(r){return r!==""}function Ul(r,e){const t=e.numSpotLightShadows+e.numSpotLightMaps-e.numSpotLightShadowsWithMaps;return r.replace(/NUM_DIR_LIGHTS/g,e.numDirLights).replace(/NUM_SPOT_LIGHTS/g,e.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,e.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,t).replace(/NUM_RECT_AREA_LIGHTS/g,e.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,e.numPointLights).replace(/NUM_HEMI_LIGHTS/g,e.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,e.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,e.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,e.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,e.numPointLightShadows)}function Nl(r,e){return r.replace(/NUM_CLIPPING_PLANES/g,e.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,e.numClippingPlanes-e.numClipIntersection)}const hy=/^[ \t]*#include +<([\w\d./]+)>/gm;function Co(r){return r.replace(hy,fy)}const dy=new Map;function fy(r,e){let t=at[e];if(t===void 0){const n=dy.get(e);if(n!==void 0)t=at[n],console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',e,n);else throw new Error("Can not resolve #include <"+e+">")}return Co(t)}const py=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function Ol(r){return r.replace(py,my)}function my(r,e,t,n){let a="";for(let o=parseInt(e);o<parseInt(t);o++)a+=n.replace(/\[\s*i\s*\]/g,"[ "+o+" ]").replace(/UNROLLED_LOOP_INDEX/g,o);return a}function kl(r){let e=`precision ${r.precision} float;
	precision ${r.precision} int;
	precision ${r.precision} sampler2D;
	precision ${r.precision} samplerCube;
	precision ${r.precision} sampler3D;
	precision ${r.precision} sampler2DArray;
	precision ${r.precision} sampler2DShadow;
	precision ${r.precision} samplerCubeShadow;
	precision ${r.precision} sampler2DArrayShadow;
	precision ${r.precision} isampler2D;
	precision ${r.precision} isampler3D;
	precision ${r.precision} isamplerCube;
	precision ${r.precision} isampler2DArray;
	precision ${r.precision} usampler2D;
	precision ${r.precision} usampler3D;
	precision ${r.precision} usamplerCube;
	precision ${r.precision} usampler2DArray;
	`;return r.precision==="highp"?e+=`
#define HIGH_PRECISION`:r.precision==="mediump"?e+=`
#define MEDIUM_PRECISION`:r.precision==="lowp"&&(e+=`
#define LOW_PRECISION`),e}function _y(r){let e="SHADOWMAP_TYPE_BASIC";return r.shadowMapType===Xl?e="SHADOWMAP_TYPE_PCF":r.shadowMapType===jl?e="SHADOWMAP_TYPE_PCF_SOFT":r.shadowMapType===Wn&&(e="SHADOWMAP_TYPE_VSM"),e}function gy(r){let e="ENVMAP_TYPE_CUBE";if(r.envMap)switch(r.envMapMode){case nr:case ir:e="ENVMAP_TYPE_CUBE";break;case Fs:e="ENVMAP_TYPE_CUBE_UV";break}return e}function vy(r){let e="ENVMAP_MODE_REFLECTION";return r.envMap&&r.envMapMode===ir&&(e="ENVMAP_MODE_REFRACTION"),e}function xy(r){let e="ENVMAP_BLENDING_NONE";if(r.envMap)switch(r.combine){case $l:e="ENVMAP_BLENDING_MULTIPLY";break;case s_:e="ENVMAP_BLENDING_MIX";break;case a_:e="ENVMAP_BLENDING_ADD";break}return e}function yy(r){const e=r.envMapCubeUVHeight;if(e===null)return null;const t=Math.log2(e)-2,n=1/e;return{texelWidth:1/(3*Math.max(Math.pow(2,t),112)),texelHeight:n,maxMip:t}}function Ey(r,e,t,n){const a=r.getContext(),o=t.defines;let l=t.vertexShader,u=t.fragmentShader;const p=_y(t),f=gy(t),_=vy(t),v=xy(t),x=yy(t),E=cy(t),R=ly(o),C=a.createProgram();let y,m,N=t.glslVersion?"#version "+t.glslVersion+`
`:"";t.isRawShaderMaterial?(y=["#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,R].filter(yr).join(`
`),y.length>0&&(y+=`
`),m=["#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,R].filter(yr).join(`
`),m.length>0&&(m+=`
`)):(y=[kl(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,R,t.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",t.batching?"#define USE_BATCHING":"",t.batchingColor?"#define USE_BATCHING_COLOR":"",t.instancing?"#define USE_INSTANCING":"",t.instancingColor?"#define USE_INSTANCING_COLOR":"",t.instancingMorph?"#define USE_INSTANCING_MORPH":"",t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.map?"#define USE_MAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+_:"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.displacementMap?"#define USE_DISPLACEMENTMAP":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.mapUv?"#define MAP_UV "+t.mapUv:"",t.alphaMapUv?"#define ALPHAMAP_UV "+t.alphaMapUv:"",t.lightMapUv?"#define LIGHTMAP_UV "+t.lightMapUv:"",t.aoMapUv?"#define AOMAP_UV "+t.aoMapUv:"",t.emissiveMapUv?"#define EMISSIVEMAP_UV "+t.emissiveMapUv:"",t.bumpMapUv?"#define BUMPMAP_UV "+t.bumpMapUv:"",t.normalMapUv?"#define NORMALMAP_UV "+t.normalMapUv:"",t.displacementMapUv?"#define DISPLACEMENTMAP_UV "+t.displacementMapUv:"",t.metalnessMapUv?"#define METALNESSMAP_UV "+t.metalnessMapUv:"",t.roughnessMapUv?"#define ROUGHNESSMAP_UV "+t.roughnessMapUv:"",t.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+t.anisotropyMapUv:"",t.clearcoatMapUv?"#define CLEARCOATMAP_UV "+t.clearcoatMapUv:"",t.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+t.clearcoatNormalMapUv:"",t.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+t.clearcoatRoughnessMapUv:"",t.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+t.iridescenceMapUv:"",t.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+t.iridescenceThicknessMapUv:"",t.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+t.sheenColorMapUv:"",t.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+t.sheenRoughnessMapUv:"",t.specularMapUv?"#define SPECULARMAP_UV "+t.specularMapUv:"",t.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+t.specularColorMapUv:"",t.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+t.specularIntensityMapUv:"",t.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+t.transmissionMapUv:"",t.thicknessMapUv?"#define THICKNESSMAP_UV "+t.thicknessMapUv:"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexColors?"#define USE_COLOR":"",t.vertexAlphas?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.flatShading?"#define FLAT_SHADED":"",t.skinning?"#define USE_SKINNING":"",t.morphTargets?"#define USE_MORPHTARGETS":"",t.morphNormals&&t.flatShading===!1?"#define USE_MORPHNORMALS":"",t.morphColors?"#define USE_MORPHCOLORS":"",t.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+t.morphTextureStride:"",t.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+t.morphTargetsCount:"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+p:"",t.sizeAttenuation?"#define USE_SIZEATTENUATION":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",t.reversedDepthBuffer?"#define USE_REVERSEDEPTHBUF":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(yr).join(`
`),m=[kl(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,R,t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",t.map?"#define USE_MAP":"",t.matcap?"#define USE_MATCAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+f:"",t.envMap?"#define "+_:"",t.envMap?"#define "+v:"",x?"#define CUBEUV_TEXEL_WIDTH "+x.texelWidth:"",x?"#define CUBEUV_TEXEL_HEIGHT "+x.texelHeight:"",x?"#define CUBEUV_MAX_MIP "+x.maxMip+".0":"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoat?"#define USE_CLEARCOAT":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.dispersion?"#define USE_DISPERSION":"",t.iridescence?"#define USE_IRIDESCENCE":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaTest?"#define USE_ALPHATEST":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.sheen?"#define USE_SHEEN":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexColors||t.instancingColor||t.batchingColor?"#define USE_COLOR":"",t.vertexAlphas?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.gradientMap?"#define USE_GRADIENTMAP":"",t.flatShading?"#define FLAT_SHADED":"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+p:"",t.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",t.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",t.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",t.reversedDepthBuffer?"#define USE_REVERSEDEPTHBUF":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",t.toneMapping!==ai?"#define TONE_MAPPING":"",t.toneMapping!==ai?at.tonemapping_pars_fragment:"",t.toneMapping!==ai?ay("toneMapping",t.toneMapping):"",t.dithering?"#define DITHERING":"",t.opaque?"#define OPAQUE":"",at.colorspace_pars_fragment,sy("linearToOutputTexel",t.outputColorSpace),oy(),t.useDepthPacking?"#define DEPTH_PACKING "+t.depthPacking:"",`
`].filter(yr).join(`
`)),l=Co(l),l=Ul(l,t),l=Nl(l,t),u=Co(u),u=Ul(u,t),u=Nl(u,t),l=Ol(l),u=Ol(u),t.isRawShaderMaterial!==!0&&(N=`#version 300 es
`,y=[E,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+y,m=["#define varying in",t.glslVersion===Hc?"":"layout(location = 0) out highp vec4 pc_fragColor;",t.glslVersion===Hc?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+m);const I=N+y+l,L=N+m+u,B=Ll(a,a.VERTEX_SHADER,I),D=Ll(a,a.FRAGMENT_SHADER,L);a.attachShader(C,B),a.attachShader(C,D),t.index0AttributeName!==void 0?a.bindAttribLocation(C,0,t.index0AttributeName):t.morphTargets===!0&&a.bindAttribLocation(C,0,"position"),a.linkProgram(C);function H(O){if(r.debug.checkShaderErrors){const te=a.getProgramInfoLog(C)||"",ee=a.getShaderInfoLog(B)||"",Z=a.getShaderInfoLog(D)||"",he=te.trim(),ae=ee.trim(),Se=Z.trim();let re=!0,Ae=!0;if(a.getProgramParameter(C,a.LINK_STATUS)===!1)if(re=!1,typeof r.debug.onShaderError=="function")r.debug.onShaderError(a,C,B,D);else{const De=Fl(a,B,"vertex"),Ve=Fl(a,D,"fragment");console.error("THREE.WebGLProgram: Shader Error "+a.getError()+" - VALIDATE_STATUS "+a.getProgramParameter(C,a.VALIDATE_STATUS)+`

Material Name: `+O.name+`
Material Type: `+O.type+`

Program Info Log: `+he+`
`+De+`
`+Ve)}else he!==""?console.warn("THREE.WebGLProgram: Program Info Log:",he):(ae===""||Se==="")&&(Ae=!1);Ae&&(O.diagnostics={runnable:re,programLog:he,vertexShader:{log:ae,prefix:y},fragmentShader:{log:Se,prefix:m}})}a.deleteShader(B),a.deleteShader(D),q=new Rs(a,C),P=uy(a,C)}let q;this.getUniforms=function(){return q===void 0&&H(this),q};let P;this.getAttributes=function(){return P===void 0&&H(this),P};let M=t.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return M===!1&&(M=a.getProgramParameter(C,ty)),M},this.destroy=function(){n.releaseStatesOfProgram(this),a.deleteProgram(C),this.program=void 0},this.type=t.shaderType,this.name=t.shaderName,this.id=ny++,this.cacheKey=e,this.usedTimes=1,this.program=C,this.vertexShader=B,this.fragmentShader=D,this}let Sy=0;class My{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(e){const t=e.vertexShader,n=e.fragmentShader,a=this._getShaderStage(t),o=this._getShaderStage(n),l=this._getShaderCacheForMaterial(e);return l.has(a)===!1&&(l.add(a),a.usedTimes++),l.has(o)===!1&&(l.add(o),o.usedTimes++),this}remove(e){const t=this.materialCache.get(e);for(const n of t)n.usedTimes--,n.usedTimes===0&&this.shaderCache.delete(n.code);return this.materialCache.delete(e),this}getVertexShaderID(e){return this._getShaderStage(e.vertexShader).id}getFragmentShaderID(e){return this._getShaderStage(e.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(e){const t=this.materialCache;let n=t.get(e);return n===void 0&&(n=new Set,t.set(e,n)),n}_getShaderStage(e){const t=this.shaderCache;let n=t.get(e);return n===void 0&&(n=new Ty(e),t.set(e,n)),n}}class Ty{constructor(e){this.id=Sy++,this.code=e,this.usedTimes=0}}function by(r,e,t,n,a,o,l){const u=new ko,p=new My,f=new Set,_=[],v=a.logarithmicDepthBuffer,x=a.vertexTextures;let E=a.precision;const R={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distanceRGBA",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function C(P){return f.add(P),P===0?"uv":`uv${P}`}function y(P,M,O,te,ee){const Z=te.fog,he=ee.geometry,ae=P.isMeshStandardMaterial?te.environment:null,Se=(P.isMeshStandardMaterial?t:e).get(P.envMap||ae),re=Se&&Se.mapping===Fs?Se.image.height:null,Ae=R[P.type];P.precision!==null&&(E=a.getMaxPrecision(P.precision),E!==P.precision&&console.warn("THREE.WebGLProgram.getParameters:",P.precision,"not supported, using",E,"instead."));const De=he.morphAttributes.position||he.morphAttributes.normal||he.morphAttributes.color,Ve=De!==void 0?De.length:0;let tt=0;he.morphAttributes.position!==void 0&&(tt=1),he.morphAttributes.normal!==void 0&&(tt=2),he.morphAttributes.color!==void 0&&(tt=3);let xt,Ze,ie,Te;if(Ae){const rt=Cn[Ae];xt=rt.vertexShader,Ze=rt.fragmentShader}else xt=P.vertexShader,Ze=P.fragmentShader,p.update(P),ie=p.getVertexShaderID(P),Te=p.getFragmentShaderID(P);const Ee=r.getRenderTarget(),ue=r.state.buffers.depth.getReversed(),ve=ee.isInstancedMesh===!0,Ye=ee.isBatchedMesh===!0,Ct=!!P.map,Qe=!!P.matcap,k=!!Se,_t=!!P.aoMap,We=!!P.lightMap,ft=!!P.bumpMap,Ge=!!P.normalMap,At=!!P.displacementMap,Le=!!P.emissiveMap,Je=!!P.metalnessMap,Pt=!!P.roughnessMap,Et=P.anisotropy>0,U=P.clearcoat>0,w=P.dispersion>0,Y=P.iridescence>0,ne=P.sheen>0,de=P.transmission>0,se=Et&&!!P.anisotropyMap,ze=U&&!!P.clearcoatMap,Me=U&&!!P.clearcoatNormalMap,Oe=U&&!!P.clearcoatRoughnessMap,Be=Y&&!!P.iridescenceMap,xe=Y&&!!P.iridescenceThicknessMap,Pe=ne&&!!P.sheenColorMap,$e=ne&&!!P.sheenRoughnessMap,ke=!!P.specularMap,we=!!P.specularColorMap,nt=!!P.specularIntensityMap,V=de&&!!P.transmissionMap,ye=de&&!!P.thicknessMap,be=!!P.gradientMap,Ie=!!P.alphaMap,G=P.alphaTest>0,z=!!P.alphaHash,Fe=!!P.extensions;let Ke=ai;P.toneMapped&&(Ee===null||Ee.isXRRenderTarget===!0)&&(Ke=r.toneMapping);const pt={shaderID:Ae,shaderType:P.type,shaderName:P.name,vertexShader:xt,fragmentShader:Ze,defines:P.defines,customVertexShaderID:ie,customFragmentShaderID:Te,isRawShaderMaterial:P.isRawShaderMaterial===!0,glslVersion:P.glslVersion,precision:E,batching:Ye,batchingColor:Ye&&ee._colorsTexture!==null,instancing:ve,instancingColor:ve&&ee.instanceColor!==null,instancingMorph:ve&&ee.morphTexture!==null,supportsVertexTextures:x,outputColorSpace:Ee===null?r.outputColorSpace:Ee.isXRRenderTarget===!0?Ee.texture.colorSpace:rr,alphaToCoverage:!!P.alphaToCoverage,map:Ct,matcap:Qe,envMap:k,envMapMode:k&&Se.mapping,envMapCubeUVHeight:re,aoMap:_t,lightMap:We,bumpMap:ft,normalMap:Ge,displacementMap:x&&At,emissiveMap:Le,normalMapObjectSpace:Ge&&P.normalMapType===__,normalMapTangentSpace:Ge&&P.normalMapType===ru,metalnessMap:Je,roughnessMap:Pt,anisotropy:Et,anisotropyMap:se,clearcoat:U,clearcoatMap:ze,clearcoatNormalMap:Me,clearcoatRoughnessMap:Oe,dispersion:w,iridescence:Y,iridescenceMap:Be,iridescenceThicknessMap:xe,sheen:ne,sheenColorMap:Pe,sheenRoughnessMap:$e,specularMap:ke,specularColorMap:we,specularIntensityMap:nt,transmission:de,transmissionMap:V,thicknessMap:ye,gradientMap:be,opaque:P.transparent===!1&&P.blending===Ji&&P.alphaToCoverage===!1,alphaMap:Ie,alphaTest:G,alphaHash:z,combine:P.combine,mapUv:Ct&&C(P.map.channel),aoMapUv:_t&&C(P.aoMap.channel),lightMapUv:We&&C(P.lightMap.channel),bumpMapUv:ft&&C(P.bumpMap.channel),normalMapUv:Ge&&C(P.normalMap.channel),displacementMapUv:At&&C(P.displacementMap.channel),emissiveMapUv:Le&&C(P.emissiveMap.channel),metalnessMapUv:Je&&C(P.metalnessMap.channel),roughnessMapUv:Pt&&C(P.roughnessMap.channel),anisotropyMapUv:se&&C(P.anisotropyMap.channel),clearcoatMapUv:ze&&C(P.clearcoatMap.channel),clearcoatNormalMapUv:Me&&C(P.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:Oe&&C(P.clearcoatRoughnessMap.channel),iridescenceMapUv:Be&&C(P.iridescenceMap.channel),iridescenceThicknessMapUv:xe&&C(P.iridescenceThicknessMap.channel),sheenColorMapUv:Pe&&C(P.sheenColorMap.channel),sheenRoughnessMapUv:$e&&C(P.sheenRoughnessMap.channel),specularMapUv:ke&&C(P.specularMap.channel),specularColorMapUv:we&&C(P.specularColorMap.channel),specularIntensityMapUv:nt&&C(P.specularIntensityMap.channel),transmissionMapUv:V&&C(P.transmissionMap.channel),thicknessMapUv:ye&&C(P.thicknessMap.channel),alphaMapUv:Ie&&C(P.alphaMap.channel),vertexTangents:!!he.attributes.tangent&&(Ge||Et),vertexColors:P.vertexColors,vertexAlphas:P.vertexColors===!0&&!!he.attributes.color&&he.attributes.color.itemSize===4,pointsUvs:ee.isPoints===!0&&!!he.attributes.uv&&(Ct||Ie),fog:!!Z,useFog:P.fog===!0,fogExp2:!!Z&&Z.isFogExp2,flatShading:P.flatShading===!0&&P.wireframe===!1,sizeAttenuation:P.sizeAttenuation===!0,logarithmicDepthBuffer:v,reversedDepthBuffer:ue,skinning:ee.isSkinnedMesh===!0,morphTargets:he.morphAttributes.position!==void 0,morphNormals:he.morphAttributes.normal!==void 0,morphColors:he.morphAttributes.color!==void 0,morphTargetsCount:Ve,morphTextureStride:tt,numDirLights:M.directional.length,numPointLights:M.point.length,numSpotLights:M.spot.length,numSpotLightMaps:M.spotLightMap.length,numRectAreaLights:M.rectArea.length,numHemiLights:M.hemi.length,numDirLightShadows:M.directionalShadowMap.length,numPointLightShadows:M.pointShadowMap.length,numSpotLightShadows:M.spotShadowMap.length,numSpotLightShadowsWithMaps:M.numSpotLightShadowsWithMaps,numLightProbes:M.numLightProbes,numClippingPlanes:l.numPlanes,numClipIntersection:l.numIntersection,dithering:P.dithering,shadowMapEnabled:r.shadowMap.enabled&&O.length>0,shadowMapType:r.shadowMap.type,toneMapping:Ke,decodeVideoTexture:Ct&&P.map.isVideoTexture===!0&&gt.getTransfer(P.map.colorSpace)===bt,decodeVideoTextureEmissive:Le&&P.emissiveMap.isVideoTexture===!0&&gt.getTransfer(P.emissiveMap.colorSpace)===bt,premultipliedAlpha:P.premultipliedAlpha,doubleSided:P.side===Xn,flipSided:P.side===an,useDepthPacking:P.depthPacking>=0,depthPacking:P.depthPacking||0,index0AttributeName:P.index0AttributeName,extensionClipCullDistance:Fe&&P.extensions.clipCullDistance===!0&&n.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(Fe&&P.extensions.multiDraw===!0||Ye)&&n.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:n.has("KHR_parallel_shader_compile"),customProgramCacheKey:P.customProgramCacheKey()};return pt.vertexUv1s=f.has(1),pt.vertexUv2s=f.has(2),pt.vertexUv3s=f.has(3),f.clear(),pt}function m(P){const M=[];if(P.shaderID?M.push(P.shaderID):(M.push(P.customVertexShaderID),M.push(P.customFragmentShaderID)),P.defines!==void 0)for(const O in P.defines)M.push(O),M.push(P.defines[O]);return P.isRawShaderMaterial===!1&&(N(M,P),I(M,P),M.push(r.outputColorSpace)),M.push(P.customProgramCacheKey),M.join()}function N(P,M){P.push(M.precision),P.push(M.outputColorSpace),P.push(M.envMapMode),P.push(M.envMapCubeUVHeight),P.push(M.mapUv),P.push(M.alphaMapUv),P.push(M.lightMapUv),P.push(M.aoMapUv),P.push(M.bumpMapUv),P.push(M.normalMapUv),P.push(M.displacementMapUv),P.push(M.emissiveMapUv),P.push(M.metalnessMapUv),P.push(M.roughnessMapUv),P.push(M.anisotropyMapUv),P.push(M.clearcoatMapUv),P.push(M.clearcoatNormalMapUv),P.push(M.clearcoatRoughnessMapUv),P.push(M.iridescenceMapUv),P.push(M.iridescenceThicknessMapUv),P.push(M.sheenColorMapUv),P.push(M.sheenRoughnessMapUv),P.push(M.specularMapUv),P.push(M.specularColorMapUv),P.push(M.specularIntensityMapUv),P.push(M.transmissionMapUv),P.push(M.thicknessMapUv),P.push(M.combine),P.push(M.fogExp2),P.push(M.sizeAttenuation),P.push(M.morphTargetsCount),P.push(M.morphAttributeCount),P.push(M.numDirLights),P.push(M.numPointLights),P.push(M.numSpotLights),P.push(M.numSpotLightMaps),P.push(M.numHemiLights),P.push(M.numRectAreaLights),P.push(M.numDirLightShadows),P.push(M.numPointLightShadows),P.push(M.numSpotLightShadows),P.push(M.numSpotLightShadowsWithMaps),P.push(M.numLightProbes),P.push(M.shadowMapType),P.push(M.toneMapping),P.push(M.numClippingPlanes),P.push(M.numClipIntersection),P.push(M.depthPacking)}function I(P,M){u.disableAll(),M.supportsVertexTextures&&u.enable(0),M.instancing&&u.enable(1),M.instancingColor&&u.enable(2),M.instancingMorph&&u.enable(3),M.matcap&&u.enable(4),M.envMap&&u.enable(5),M.normalMapObjectSpace&&u.enable(6),M.normalMapTangentSpace&&u.enable(7),M.clearcoat&&u.enable(8),M.iridescence&&u.enable(9),M.alphaTest&&u.enable(10),M.vertexColors&&u.enable(11),M.vertexAlphas&&u.enable(12),M.vertexUv1s&&u.enable(13),M.vertexUv2s&&u.enable(14),M.vertexUv3s&&u.enable(15),M.vertexTangents&&u.enable(16),M.anisotropy&&u.enable(17),M.alphaHash&&u.enable(18),M.batching&&u.enable(19),M.dispersion&&u.enable(20),M.batchingColor&&u.enable(21),M.gradientMap&&u.enable(22),P.push(u.mask),u.disableAll(),M.fog&&u.enable(0),M.useFog&&u.enable(1),M.flatShading&&u.enable(2),M.logarithmicDepthBuffer&&u.enable(3),M.reversedDepthBuffer&&u.enable(4),M.skinning&&u.enable(5),M.morphTargets&&u.enable(6),M.morphNormals&&u.enable(7),M.morphColors&&u.enable(8),M.premultipliedAlpha&&u.enable(9),M.shadowMapEnabled&&u.enable(10),M.doubleSided&&u.enable(11),M.flipSided&&u.enable(12),M.useDepthPacking&&u.enable(13),M.dithering&&u.enable(14),M.transmission&&u.enable(15),M.sheen&&u.enable(16),M.opaque&&u.enable(17),M.pointsUvs&&u.enable(18),M.decodeVideoTexture&&u.enable(19),M.decodeVideoTextureEmissive&&u.enable(20),M.alphaToCoverage&&u.enable(21),P.push(u.mask)}function L(P){const M=R[P.type];let O;if(M){const te=Cn[M];O=j_.clone(te.uniforms)}else O=P.uniforms;return O}function B(P,M){let O;for(let te=0,ee=_.length;te<ee;te++){const Z=_[te];if(Z.cacheKey===M){O=Z,++O.usedTimes;break}}return O===void 0&&(O=new Ey(r,M,P,o),_.push(O)),O}function D(P){if(--P.usedTimes===0){const M=_.indexOf(P);_[M]=_[_.length-1],_.pop(),P.destroy()}}function H(P){p.remove(P)}function q(){p.dispose()}return{getParameters:y,getProgramCacheKey:m,getUniforms:L,acquireProgram:B,releaseProgram:D,releaseShaderCache:H,programs:_,dispose:q}}function wy(){let r=new WeakMap;function e(l){return r.has(l)}function t(l){let u=r.get(l);return u===void 0&&(u={},r.set(l,u)),u}function n(l){r.delete(l)}function a(l,u,p){r.get(l)[u]=p}function o(){r=new WeakMap}return{has:e,get:t,remove:n,update:a,dispose:o}}function Ay(r,e){return r.groupOrder!==e.groupOrder?r.groupOrder-e.groupOrder:r.renderOrder!==e.renderOrder?r.renderOrder-e.renderOrder:r.material.id!==e.material.id?r.material.id-e.material.id:r.z!==e.z?r.z-e.z:r.id-e.id}function Bl(r,e){return r.groupOrder!==e.groupOrder?r.groupOrder-e.groupOrder:r.renderOrder!==e.renderOrder?r.renderOrder-e.renderOrder:r.z!==e.z?e.z-r.z:r.id-e.id}function zl(){const r=[];let e=0;const t=[],n=[],a=[];function o(){e=0,t.length=0,n.length=0,a.length=0}function l(v,x,E,R,C,y){let m=r[e];return m===void 0?(m={id:v.id,object:v,geometry:x,material:E,groupOrder:R,renderOrder:v.renderOrder,z:C,group:y},r[e]=m):(m.id=v.id,m.object=v,m.geometry=x,m.material=E,m.groupOrder=R,m.renderOrder=v.renderOrder,m.z=C,m.group=y),e++,m}function u(v,x,E,R,C,y){const m=l(v,x,E,R,C,y);E.transmission>0?n.push(m):E.transparent===!0?a.push(m):t.push(m)}function p(v,x,E,R,C,y){const m=l(v,x,E,R,C,y);E.transmission>0?n.unshift(m):E.transparent===!0?a.unshift(m):t.unshift(m)}function f(v,x){t.length>1&&t.sort(v||Ay),n.length>1&&n.sort(x||Bl),a.length>1&&a.sort(x||Bl)}function _(){for(let v=e,x=r.length;v<x;v++){const E=r[v];if(E.id===null)break;E.id=null,E.object=null,E.geometry=null,E.material=null,E.group=null}}return{opaque:t,transmissive:n,transparent:a,init:o,push:u,unshift:p,finish:_,sort:f}}function Ry(){let r=new WeakMap;function e(n,a){const o=r.get(n);let l;return o===void 0?(l=new zl,r.set(n,[l])):a>=o.length?(l=new zl,o.push(l)):l=o[a],l}function t(){r=new WeakMap}return{get:e,dispose:t}}function Cy(){const r={};return{get:function(e){if(r[e.id]!==void 0)return r[e.id];let t;switch(e.type){case"DirectionalLight":t={direction:new X,color:new ot};break;case"SpotLight":t={position:new X,direction:new X,color:new ot,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":t={position:new X,color:new ot,distance:0,decay:0};break;case"HemisphereLight":t={direction:new X,skyColor:new ot,groundColor:new ot};break;case"RectAreaLight":t={color:new ot,position:new X,halfWidth:new X,halfHeight:new X};break}return r[e.id]=t,t}}}function Py(){const r={};return{get:function(e){if(r[e.id]!==void 0)return r[e.id];let t;switch(e.type){case"DirectionalLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new et};break;case"SpotLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new et};break;case"PointLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new et,shadowCameraNear:1,shadowCameraFar:1e3};break}return r[e.id]=t,t}}}let Dy=0;function Ly(r,e){return(e.castShadow?2:0)-(r.castShadow?2:0)+(e.map?1:0)-(r.map?1:0)}function Iy(r){const e=new Cy,t=Py(),n={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let f=0;f<9;f++)n.probe.push(new X);const a=new X,o=new Ft,l=new Ft;function u(f){let _=0,v=0,x=0;for(let P=0;P<9;P++)n.probe[P].set(0,0,0);let E=0,R=0,C=0,y=0,m=0,N=0,I=0,L=0,B=0,D=0,H=0;f.sort(Ly);for(let P=0,M=f.length;P<M;P++){const O=f[P],te=O.color,ee=O.intensity,Z=O.distance,he=O.shadow&&O.shadow.map?O.shadow.map.texture:null;if(O.isAmbientLight)_+=te.r*ee,v+=te.g*ee,x+=te.b*ee;else if(O.isLightProbe){for(let ae=0;ae<9;ae++)n.probe[ae].addScaledVector(O.sh.coefficients[ae],ee);H++}else if(O.isDirectionalLight){const ae=e.get(O);if(ae.color.copy(O.color).multiplyScalar(O.intensity),O.castShadow){const Se=O.shadow,re=t.get(O);re.shadowIntensity=Se.intensity,re.shadowBias=Se.bias,re.shadowNormalBias=Se.normalBias,re.shadowRadius=Se.radius,re.shadowMapSize=Se.mapSize,n.directionalShadow[E]=re,n.directionalShadowMap[E]=he,n.directionalShadowMatrix[E]=O.shadow.matrix,N++}n.directional[E]=ae,E++}else if(O.isSpotLight){const ae=e.get(O);ae.position.setFromMatrixPosition(O.matrixWorld),ae.color.copy(te).multiplyScalar(ee),ae.distance=Z,ae.coneCos=Math.cos(O.angle),ae.penumbraCos=Math.cos(O.angle*(1-O.penumbra)),ae.decay=O.decay,n.spot[C]=ae;const Se=O.shadow;if(O.map&&(n.spotLightMap[B]=O.map,B++,Se.updateMatrices(O),O.castShadow&&D++),n.spotLightMatrix[C]=Se.matrix,O.castShadow){const re=t.get(O);re.shadowIntensity=Se.intensity,re.shadowBias=Se.bias,re.shadowNormalBias=Se.normalBias,re.shadowRadius=Se.radius,re.shadowMapSize=Se.mapSize,n.spotShadow[C]=re,n.spotShadowMap[C]=he,L++}C++}else if(O.isRectAreaLight){const ae=e.get(O);ae.color.copy(te).multiplyScalar(ee),ae.halfWidth.set(O.width*.5,0,0),ae.halfHeight.set(0,O.height*.5,0),n.rectArea[y]=ae,y++}else if(O.isPointLight){const ae=e.get(O);if(ae.color.copy(O.color).multiplyScalar(O.intensity),ae.distance=O.distance,ae.decay=O.decay,O.castShadow){const Se=O.shadow,re=t.get(O);re.shadowIntensity=Se.intensity,re.shadowBias=Se.bias,re.shadowNormalBias=Se.normalBias,re.shadowRadius=Se.radius,re.shadowMapSize=Se.mapSize,re.shadowCameraNear=Se.camera.near,re.shadowCameraFar=Se.camera.far,n.pointShadow[R]=re,n.pointShadowMap[R]=he,n.pointShadowMatrix[R]=O.shadow.matrix,I++}n.point[R]=ae,R++}else if(O.isHemisphereLight){const ae=e.get(O);ae.skyColor.copy(O.color).multiplyScalar(ee),ae.groundColor.copy(O.groundColor).multiplyScalar(ee),n.hemi[m]=ae,m++}}y>0&&(r.has("OES_texture_float_linear")===!0?(n.rectAreaLTC1=Ce.LTC_FLOAT_1,n.rectAreaLTC2=Ce.LTC_FLOAT_2):(n.rectAreaLTC1=Ce.LTC_HALF_1,n.rectAreaLTC2=Ce.LTC_HALF_2)),n.ambient[0]=_,n.ambient[1]=v,n.ambient[2]=x;const q=n.hash;(q.directionalLength!==E||q.pointLength!==R||q.spotLength!==C||q.rectAreaLength!==y||q.hemiLength!==m||q.numDirectionalShadows!==N||q.numPointShadows!==I||q.numSpotShadows!==L||q.numSpotMaps!==B||q.numLightProbes!==H)&&(n.directional.length=E,n.spot.length=C,n.rectArea.length=y,n.point.length=R,n.hemi.length=m,n.directionalShadow.length=N,n.directionalShadowMap.length=N,n.pointShadow.length=I,n.pointShadowMap.length=I,n.spotShadow.length=L,n.spotShadowMap.length=L,n.directionalShadowMatrix.length=N,n.pointShadowMatrix.length=I,n.spotLightMatrix.length=L+B-D,n.spotLightMap.length=B,n.numSpotLightShadowsWithMaps=D,n.numLightProbes=H,q.directionalLength=E,q.pointLength=R,q.spotLength=C,q.rectAreaLength=y,q.hemiLength=m,q.numDirectionalShadows=N,q.numPointShadows=I,q.numSpotShadows=L,q.numSpotMaps=B,q.numLightProbes=H,n.version=Dy++)}function p(f,_){let v=0,x=0,E=0,R=0,C=0;const y=_.matrixWorldInverse;for(let m=0,N=f.length;m<N;m++){const I=f[m];if(I.isDirectionalLight){const L=n.directional[v];L.direction.setFromMatrixPosition(I.matrixWorld),a.setFromMatrixPosition(I.target.matrixWorld),L.direction.sub(a),L.direction.transformDirection(y),v++}else if(I.isSpotLight){const L=n.spot[E];L.position.setFromMatrixPosition(I.matrixWorld),L.position.applyMatrix4(y),L.direction.setFromMatrixPosition(I.matrixWorld),a.setFromMatrixPosition(I.target.matrixWorld),L.direction.sub(a),L.direction.transformDirection(y),E++}else if(I.isRectAreaLight){const L=n.rectArea[R];L.position.setFromMatrixPosition(I.matrixWorld),L.position.applyMatrix4(y),l.identity(),o.copy(I.matrixWorld),o.premultiply(y),l.extractRotation(o),L.halfWidth.set(I.width*.5,0,0),L.halfHeight.set(0,I.height*.5,0),L.halfWidth.applyMatrix4(l),L.halfHeight.applyMatrix4(l),R++}else if(I.isPointLight){const L=n.point[x];L.position.setFromMatrixPosition(I.matrixWorld),L.position.applyMatrix4(y),x++}else if(I.isHemisphereLight){const L=n.hemi[C];L.direction.setFromMatrixPosition(I.matrixWorld),L.direction.transformDirection(y),C++}}}return{setup:u,setupView:p,state:n}}function Hl(r){const e=new Iy(r),t=[],n=[];function a(_){f.camera=_,t.length=0,n.length=0}function o(_){t.push(_)}function l(_){n.push(_)}function u(){e.setup(t)}function p(_){e.setupView(t,_)}const f={lightsArray:t,shadowsArray:n,camera:null,lights:e,transmissionRenderTarget:{}};return{init:a,state:f,setupLights:u,setupLightsView:p,pushLight:o,pushShadow:l}}function Fy(r){let e=new WeakMap;function t(a,o=0){const l=e.get(a);let u;return l===void 0?(u=new Hl(r),e.set(a,[u])):o>=l.length?(u=new Hl(r),l.push(u)):u=l[o],u}function n(){e=new WeakMap}return{get:t,dispose:n}}const Uy=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,Ny=`uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
#include <packing>
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = unpackRGBATo2Half( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ) );
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = unpackRGBAToDepth( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ) );
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( squared_mean - mean * mean );
	gl_FragColor = pack2HalfToRGBA( vec2( mean, std_dev ) );
}`;function Oy(r,e,t){let n=new Ho;const a=new et,o=new et,l=new Ut,u=new ig({depthPacking:m_}),p=new rg,f={},_=t.maxTextureSize,v={[oi]:an,[an]:oi,[Xn]:Xn},x=new ci({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new et},radius:{value:4}},vertexShader:Uy,fragmentShader:Ny}),E=x.clone();E.defines.HORIZONTAL_PASS=1;const R=new cn;R.setAttribute("position",new Ln(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));const C=new _n(R,x),y=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=Xl;let m=this.type;this.render=function(D,H,q){if(y.enabled===!1||y.autoUpdate===!1&&y.needsUpdate===!1||D.length===0)return;const P=r.getRenderTarget(),M=r.getActiveCubeFace(),O=r.getActiveMipmapLevel(),te=r.state;te.setBlending(si),te.buffers.depth.getReversed()?te.buffers.color.setClear(0,0,0,0):te.buffers.color.setClear(1,1,1,1),te.buffers.depth.setTest(!0),te.setScissorTest(!1);const ee=m!==Wn&&this.type===Wn,Z=m===Wn&&this.type!==Wn;for(let he=0,ae=D.length;he<ae;he++){const Se=D[he],re=Se.shadow;if(re===void 0){console.warn("THREE.WebGLShadowMap:",Se,"has no shadow.");continue}if(re.autoUpdate===!1&&re.needsUpdate===!1)continue;a.copy(re.mapSize);const Ae=re.getFrameExtents();if(a.multiply(Ae),o.copy(re.mapSize),(a.x>_||a.y>_)&&(a.x>_&&(o.x=Math.floor(_/Ae.x),a.x=o.x*Ae.x,re.mapSize.x=o.x),a.y>_&&(o.y=Math.floor(_/Ae.y),a.y=o.y*Ae.y,re.mapSize.y=o.y)),re.map===null||ee===!0||Z===!0){const Ve=this.type!==Wn?{minFilter:Tn,magFilter:Tn}:{};re.map!==null&&re.map.dispose(),re.map=new Pi(a.x,a.y,Ve),re.map.texture.name=Se.name+".shadowMap",re.camera.updateProjectionMatrix()}r.setRenderTarget(re.map),r.clear();const De=re.getViewportCount();for(let Ve=0;Ve<De;Ve++){const tt=re.getViewport(Ve);l.set(o.x*tt.x,o.y*tt.y,o.x*tt.z,o.y*tt.w),te.viewport(l),re.updateMatrices(Se,Ve),n=re.getFrustum(),L(H,q,re.camera,Se,this.type)}re.isPointLightShadow!==!0&&this.type===Wn&&N(re,q),re.needsUpdate=!1}m=this.type,y.needsUpdate=!1,r.setRenderTarget(P,M,O)};function N(D,H){const q=e.update(C);x.defines.VSM_SAMPLES!==D.blurSamples&&(x.defines.VSM_SAMPLES=D.blurSamples,E.defines.VSM_SAMPLES=D.blurSamples,x.needsUpdate=!0,E.needsUpdate=!0),D.mapPass===null&&(D.mapPass=new Pi(a.x,a.y)),x.uniforms.shadow_pass.value=D.map.texture,x.uniforms.resolution.value=D.mapSize,x.uniforms.radius.value=D.radius,r.setRenderTarget(D.mapPass),r.clear(),r.renderBufferDirect(H,null,q,x,C,null),E.uniforms.shadow_pass.value=D.mapPass.texture,E.uniforms.resolution.value=D.mapSize,E.uniforms.radius.value=D.radius,r.setRenderTarget(D.map),r.clear(),r.renderBufferDirect(H,null,q,E,C,null)}function I(D,H,q,P){let M=null;const O=q.isPointLight===!0?D.customDistanceMaterial:D.customDepthMaterial;if(O!==void 0)M=O;else if(M=q.isPointLight===!0?p:u,r.localClippingEnabled&&H.clipShadows===!0&&Array.isArray(H.clippingPlanes)&&H.clippingPlanes.length!==0||H.displacementMap&&H.displacementScale!==0||H.alphaMap&&H.alphaTest>0||H.map&&H.alphaTest>0||H.alphaToCoverage===!0){const te=M.uuid,ee=H.uuid;let Z=f[te];Z===void 0&&(Z={},f[te]=Z);let he=Z[ee];he===void 0&&(he=M.clone(),Z[ee]=he,H.addEventListener("dispose",B)),M=he}if(M.visible=H.visible,M.wireframe=H.wireframe,P===Wn?M.side=H.shadowSide!==null?H.shadowSide:H.side:M.side=H.shadowSide!==null?H.shadowSide:v[H.side],M.alphaMap=H.alphaMap,M.alphaTest=H.alphaToCoverage===!0?.5:H.alphaTest,M.map=H.map,M.clipShadows=H.clipShadows,M.clippingPlanes=H.clippingPlanes,M.clipIntersection=H.clipIntersection,M.displacementMap=H.displacementMap,M.displacementScale=H.displacementScale,M.displacementBias=H.displacementBias,M.wireframeLinewidth=H.wireframeLinewidth,M.linewidth=H.linewidth,q.isPointLight===!0&&M.isMeshDistanceMaterial===!0){const te=r.properties.get(M);te.light=q}return M}function L(D,H,q,P,M){if(D.visible===!1)return;if(D.layers.test(H.layers)&&(D.isMesh||D.isLine||D.isPoints)&&(D.castShadow||D.receiveShadow&&M===Wn)&&(!D.frustumCulled||n.intersectsObject(D))){D.modelViewMatrix.multiplyMatrices(q.matrixWorldInverse,D.matrixWorld);const ee=e.update(D),Z=D.material;if(Array.isArray(Z)){const he=ee.groups;for(let ae=0,Se=he.length;ae<Se;ae++){const re=he[ae],Ae=Z[re.materialIndex];if(Ae&&Ae.visible){const De=I(D,Ae,P,M);D.onBeforeShadow(r,D,H,q,ee,De,re),r.renderBufferDirect(q,null,ee,De,D,re),D.onAfterShadow(r,D,H,q,ee,De,re)}}}else if(Z.visible){const he=I(D,Z,P,M);D.onBeforeShadow(r,D,H,q,ee,he,null),r.renderBufferDirect(q,null,ee,he,D,null),D.onAfterShadow(r,D,H,q,ee,he,null)}}const te=D.children;for(let ee=0,Z=te.length;ee<Z;ee++)L(te[ee],H,q,P,M)}function B(D){D.target.removeEventListener("dispose",B);for(const q in f){const P=f[q],M=D.target.uuid;M in P&&(P[M].dispose(),delete P[M])}}}const ky={[Ga]:Wa,[Xa]:qa,[ja]:Ya,[tr]:$a,[Wa]:Ga,[qa]:Xa,[Ya]:ja,[$a]:tr};function By(r,e){function t(){let V=!1;const ye=new Ut;let be=null;const Ie=new Ut(0,0,0,0);return{setMask:function(G){be!==G&&!V&&(r.colorMask(G,G,G,G),be=G)},setLocked:function(G){V=G},setClear:function(G,z,Fe,Ke,pt){pt===!0&&(G*=Ke,z*=Ke,Fe*=Ke),ye.set(G,z,Fe,Ke),Ie.equals(ye)===!1&&(r.clearColor(G,z,Fe,Ke),Ie.copy(ye))},reset:function(){V=!1,be=null,Ie.set(-1,0,0,0)}}}function n(){let V=!1,ye=!1,be=null,Ie=null,G=null;return{setReversed:function(z){if(ye!==z){const Fe=e.get("EXT_clip_control");z?Fe.clipControlEXT(Fe.LOWER_LEFT_EXT,Fe.ZERO_TO_ONE_EXT):Fe.clipControlEXT(Fe.LOWER_LEFT_EXT,Fe.NEGATIVE_ONE_TO_ONE_EXT),ye=z;const Ke=G;G=null,this.setClear(Ke)}},getReversed:function(){return ye},setTest:function(z){z?Ee(r.DEPTH_TEST):ue(r.DEPTH_TEST)},setMask:function(z){be!==z&&!V&&(r.depthMask(z),be=z)},setFunc:function(z){if(ye&&(z=ky[z]),Ie!==z){switch(z){case Ga:r.depthFunc(r.NEVER);break;case Wa:r.depthFunc(r.ALWAYS);break;case Xa:r.depthFunc(r.LESS);break;case tr:r.depthFunc(r.LEQUAL);break;case ja:r.depthFunc(r.EQUAL);break;case $a:r.depthFunc(r.GEQUAL);break;case qa:r.depthFunc(r.GREATER);break;case Ya:r.depthFunc(r.NOTEQUAL);break;default:r.depthFunc(r.LEQUAL)}Ie=z}},setLocked:function(z){V=z},setClear:function(z){G!==z&&(ye&&(z=1-z),r.clearDepth(z),G=z)},reset:function(){V=!1,be=null,Ie=null,G=null,ye=!1}}}function a(){let V=!1,ye=null,be=null,Ie=null,G=null,z=null,Fe=null,Ke=null,pt=null;return{setTest:function(rt){V||(rt?Ee(r.STENCIL_TEST):ue(r.STENCIL_TEST))},setMask:function(rt){ye!==rt&&!V&&(r.stencilMask(rt),ye=rt)},setFunc:function(rt,gn,Ot){(be!==rt||Ie!==gn||G!==Ot)&&(r.stencilFunc(rt,gn,Ot),be=rt,Ie=gn,G=Ot)},setOp:function(rt,gn,Ot){(z!==rt||Fe!==gn||Ke!==Ot)&&(r.stencilOp(rt,gn,Ot),z=rt,Fe=gn,Ke=Ot)},setLocked:function(rt){V=rt},setClear:function(rt){pt!==rt&&(r.clearStencil(rt),pt=rt)},reset:function(){V=!1,ye=null,be=null,Ie=null,G=null,z=null,Fe=null,Ke=null,pt=null}}}const o=new t,l=new n,u=new a,p=new WeakMap,f=new WeakMap;let _={},v={},x=new WeakMap,E=[],R=null,C=!1,y=null,m=null,N=null,I=null,L=null,B=null,D=null,H=new ot(0,0,0),q=0,P=!1,M=null,O=null,te=null,ee=null,Z=null;const he=r.getParameter(r.MAX_COMBINED_TEXTURE_IMAGE_UNITS);let ae=!1,Se=0;const re=r.getParameter(r.VERSION);re.indexOf("WebGL")!==-1?(Se=parseFloat(/^WebGL (\d)/.exec(re)[1]),ae=Se>=1):re.indexOf("OpenGL ES")!==-1&&(Se=parseFloat(/^OpenGL ES (\d)/.exec(re)[1]),ae=Se>=2);let Ae=null,De={};const Ve=r.getParameter(r.SCISSOR_BOX),tt=r.getParameter(r.VIEWPORT),xt=new Ut().fromArray(Ve),Ze=new Ut().fromArray(tt);function ie(V,ye,be,Ie){const G=new Uint8Array(4),z=r.createTexture();r.bindTexture(V,z),r.texParameteri(V,r.TEXTURE_MIN_FILTER,r.NEAREST),r.texParameteri(V,r.TEXTURE_MAG_FILTER,r.NEAREST);for(let Fe=0;Fe<be;Fe++)V===r.TEXTURE_3D||V===r.TEXTURE_2D_ARRAY?r.texImage3D(ye,0,r.RGBA,1,1,Ie,0,r.RGBA,r.UNSIGNED_BYTE,G):r.texImage2D(ye+Fe,0,r.RGBA,1,1,0,r.RGBA,r.UNSIGNED_BYTE,G);return z}const Te={};Te[r.TEXTURE_2D]=ie(r.TEXTURE_2D,r.TEXTURE_2D,1),Te[r.TEXTURE_CUBE_MAP]=ie(r.TEXTURE_CUBE_MAP,r.TEXTURE_CUBE_MAP_POSITIVE_X,6),Te[r.TEXTURE_2D_ARRAY]=ie(r.TEXTURE_2D_ARRAY,r.TEXTURE_2D_ARRAY,1,1),Te[r.TEXTURE_3D]=ie(r.TEXTURE_3D,r.TEXTURE_3D,1,1),o.setClear(0,0,0,1),l.setClear(1),u.setClear(0),Ee(r.DEPTH_TEST),l.setFunc(tr),ft(!1),Ge(Uc),Ee(r.CULL_FACE),_t(si);function Ee(V){_[V]!==!0&&(r.enable(V),_[V]=!0)}function ue(V){_[V]!==!1&&(r.disable(V),_[V]=!1)}function ve(V,ye){return v[V]!==ye?(r.bindFramebuffer(V,ye),v[V]=ye,V===r.DRAW_FRAMEBUFFER&&(v[r.FRAMEBUFFER]=ye),V===r.FRAMEBUFFER&&(v[r.DRAW_FRAMEBUFFER]=ye),!0):!1}function Ye(V,ye){let be=E,Ie=!1;if(V){be=x.get(ye),be===void 0&&(be=[],x.set(ye,be));const G=V.textures;if(be.length!==G.length||be[0]!==r.COLOR_ATTACHMENT0){for(let z=0,Fe=G.length;z<Fe;z++)be[z]=r.COLOR_ATTACHMENT0+z;be.length=G.length,Ie=!0}}else be[0]!==r.BACK&&(be[0]=r.BACK,Ie=!0);Ie&&r.drawBuffers(be)}function Ct(V){return R!==V?(r.useProgram(V),R=V,!0):!1}const Qe={[Ti]:r.FUNC_ADD,[Vm]:r.FUNC_SUBTRACT,[Gm]:r.FUNC_REVERSE_SUBTRACT};Qe[Wm]=r.MIN,Qe[Xm]=r.MAX;const k={[jm]:r.ZERO,[$m]:r.ONE,[qm]:r.SRC_COLOR,[Ha]:r.SRC_ALPHA,[e_]:r.SRC_ALPHA_SATURATE,[Jm]:r.DST_COLOR,[Km]:r.DST_ALPHA,[Ym]:r.ONE_MINUS_SRC_COLOR,[Va]:r.ONE_MINUS_SRC_ALPHA,[Qm]:r.ONE_MINUS_DST_COLOR,[Zm]:r.ONE_MINUS_DST_ALPHA,[t_]:r.CONSTANT_COLOR,[n_]:r.ONE_MINUS_CONSTANT_COLOR,[i_]:r.CONSTANT_ALPHA,[r_]:r.ONE_MINUS_CONSTANT_ALPHA};function _t(V,ye,be,Ie,G,z,Fe,Ke,pt,rt){if(V===si){C===!0&&(ue(r.BLEND),C=!1);return}if(C===!1&&(Ee(r.BLEND),C=!0),V!==Hm){if(V!==y||rt!==P){if((m!==Ti||L!==Ti)&&(r.blendEquation(r.FUNC_ADD),m=Ti,L=Ti),rt)switch(V){case Ji:r.blendFuncSeparate(r.ONE,r.ONE_MINUS_SRC_ALPHA,r.ONE,r.ONE_MINUS_SRC_ALPHA);break;case Nc:r.blendFunc(r.ONE,r.ONE);break;case Oc:r.blendFuncSeparate(r.ZERO,r.ONE_MINUS_SRC_COLOR,r.ZERO,r.ONE);break;case kc:r.blendFuncSeparate(r.DST_COLOR,r.ONE_MINUS_SRC_ALPHA,r.ZERO,r.ONE);break;default:console.error("THREE.WebGLState: Invalid blending: ",V);break}else switch(V){case Ji:r.blendFuncSeparate(r.SRC_ALPHA,r.ONE_MINUS_SRC_ALPHA,r.ONE,r.ONE_MINUS_SRC_ALPHA);break;case Nc:r.blendFuncSeparate(r.SRC_ALPHA,r.ONE,r.ONE,r.ONE);break;case Oc:console.error("THREE.WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true");break;case kc:console.error("THREE.WebGLState: MultiplyBlending requires material.premultipliedAlpha = true");break;default:console.error("THREE.WebGLState: Invalid blending: ",V);break}N=null,I=null,B=null,D=null,H.set(0,0,0),q=0,y=V,P=rt}return}G=G||ye,z=z||be,Fe=Fe||Ie,(ye!==m||G!==L)&&(r.blendEquationSeparate(Qe[ye],Qe[G]),m=ye,L=G),(be!==N||Ie!==I||z!==B||Fe!==D)&&(r.blendFuncSeparate(k[be],k[Ie],k[z],k[Fe]),N=be,I=Ie,B=z,D=Fe),(Ke.equals(H)===!1||pt!==q)&&(r.blendColor(Ke.r,Ke.g,Ke.b,pt),H.copy(Ke),q=pt),y=V,P=!1}function We(V,ye){V.side===Xn?ue(r.CULL_FACE):Ee(r.CULL_FACE);let be=V.side===an;ye&&(be=!be),ft(be),V.blending===Ji&&V.transparent===!1?_t(si):_t(V.blending,V.blendEquation,V.blendSrc,V.blendDst,V.blendEquationAlpha,V.blendSrcAlpha,V.blendDstAlpha,V.blendColor,V.blendAlpha,V.premultipliedAlpha),l.setFunc(V.depthFunc),l.setTest(V.depthTest),l.setMask(V.depthWrite),o.setMask(V.colorWrite);const Ie=V.stencilWrite;u.setTest(Ie),Ie&&(u.setMask(V.stencilWriteMask),u.setFunc(V.stencilFunc,V.stencilRef,V.stencilFuncMask),u.setOp(V.stencilFail,V.stencilZFail,V.stencilZPass)),Le(V.polygonOffset,V.polygonOffsetFactor,V.polygonOffsetUnits),V.alphaToCoverage===!0?Ee(r.SAMPLE_ALPHA_TO_COVERAGE):ue(r.SAMPLE_ALPHA_TO_COVERAGE)}function ft(V){M!==V&&(V?r.frontFace(r.CW):r.frontFace(r.CCW),M=V)}function Ge(V){V!==Bm?(Ee(r.CULL_FACE),V!==O&&(V===Uc?r.cullFace(r.BACK):V===zm?r.cullFace(r.FRONT):r.cullFace(r.FRONT_AND_BACK))):ue(r.CULL_FACE),O=V}function At(V){V!==te&&(ae&&r.lineWidth(V),te=V)}function Le(V,ye,be){V?(Ee(r.POLYGON_OFFSET_FILL),(ee!==ye||Z!==be)&&(r.polygonOffset(ye,be),ee=ye,Z=be)):ue(r.POLYGON_OFFSET_FILL)}function Je(V){V?Ee(r.SCISSOR_TEST):ue(r.SCISSOR_TEST)}function Pt(V){V===void 0&&(V=r.TEXTURE0+he-1),Ae!==V&&(r.activeTexture(V),Ae=V)}function Et(V,ye,be){be===void 0&&(Ae===null?be=r.TEXTURE0+he-1:be=Ae);let Ie=De[be];Ie===void 0&&(Ie={type:void 0,texture:void 0},De[be]=Ie),(Ie.type!==V||Ie.texture!==ye)&&(Ae!==be&&(r.activeTexture(be),Ae=be),r.bindTexture(V,ye||Te[V]),Ie.type=V,Ie.texture=ye)}function U(){const V=De[Ae];V!==void 0&&V.type!==void 0&&(r.bindTexture(V.type,null),V.type=void 0,V.texture=void 0)}function w(){try{r.compressedTexImage2D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function Y(){try{r.compressedTexImage3D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function ne(){try{r.texSubImage2D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function de(){try{r.texSubImage3D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function se(){try{r.compressedTexSubImage2D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function ze(){try{r.compressedTexSubImage3D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function Me(){try{r.texStorage2D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function Oe(){try{r.texStorage3D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function Be(){try{r.texImage2D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function xe(){try{r.texImage3D(...arguments)}catch(V){console.error("THREE.WebGLState:",V)}}function Pe(V){xt.equals(V)===!1&&(r.scissor(V.x,V.y,V.z,V.w),xt.copy(V))}function $e(V){Ze.equals(V)===!1&&(r.viewport(V.x,V.y,V.z,V.w),Ze.copy(V))}function ke(V,ye){let be=f.get(ye);be===void 0&&(be=new WeakMap,f.set(ye,be));let Ie=be.get(V);Ie===void 0&&(Ie=r.getUniformBlockIndex(ye,V.name),be.set(V,Ie))}function we(V,ye){const Ie=f.get(ye).get(V);p.get(ye)!==Ie&&(r.uniformBlockBinding(ye,Ie,V.__bindingPointIndex),p.set(ye,Ie))}function nt(){r.disable(r.BLEND),r.disable(r.CULL_FACE),r.disable(r.DEPTH_TEST),r.disable(r.POLYGON_OFFSET_FILL),r.disable(r.SCISSOR_TEST),r.disable(r.STENCIL_TEST),r.disable(r.SAMPLE_ALPHA_TO_COVERAGE),r.blendEquation(r.FUNC_ADD),r.blendFunc(r.ONE,r.ZERO),r.blendFuncSeparate(r.ONE,r.ZERO,r.ONE,r.ZERO),r.blendColor(0,0,0,0),r.colorMask(!0,!0,!0,!0),r.clearColor(0,0,0,0),r.depthMask(!0),r.depthFunc(r.LESS),l.setReversed(!1),r.clearDepth(1),r.stencilMask(4294967295),r.stencilFunc(r.ALWAYS,0,4294967295),r.stencilOp(r.KEEP,r.KEEP,r.KEEP),r.clearStencil(0),r.cullFace(r.BACK),r.frontFace(r.CCW),r.polygonOffset(0,0),r.activeTexture(r.TEXTURE0),r.bindFramebuffer(r.FRAMEBUFFER,null),r.bindFramebuffer(r.DRAW_FRAMEBUFFER,null),r.bindFramebuffer(r.READ_FRAMEBUFFER,null),r.useProgram(null),r.lineWidth(1),r.scissor(0,0,r.canvas.width,r.canvas.height),r.viewport(0,0,r.canvas.width,r.canvas.height),_={},Ae=null,De={},v={},x=new WeakMap,E=[],R=null,C=!1,y=null,m=null,N=null,I=null,L=null,B=null,D=null,H=new ot(0,0,0),q=0,P=!1,M=null,O=null,te=null,ee=null,Z=null,xt.set(0,0,r.canvas.width,r.canvas.height),Ze.set(0,0,r.canvas.width,r.canvas.height),o.reset(),l.reset(),u.reset()}return{buffers:{color:o,depth:l,stencil:u},enable:Ee,disable:ue,bindFramebuffer:ve,drawBuffers:Ye,useProgram:Ct,setBlending:_t,setMaterial:We,setFlipSided:ft,setCullFace:Ge,setLineWidth:At,setPolygonOffset:Le,setScissorTest:Je,activeTexture:Pt,bindTexture:Et,unbindTexture:U,compressedTexImage2D:w,compressedTexImage3D:Y,texImage2D:Be,texImage3D:xe,updateUBOMapping:ke,uniformBlockBinding:we,texStorage2D:Me,texStorage3D:Oe,texSubImage2D:ne,texSubImage3D:de,compressedTexSubImage2D:se,compressedTexSubImage3D:ze,scissor:Pe,viewport:$e,reset:nt}}function zy(r,e,t,n,a,o,l){const u=e.has("WEBGL_multisampled_render_to_texture")?e.get("WEBGL_multisampled_render_to_texture"):null,p=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),f=new et,_=new WeakMap;let v;const x=new WeakMap;let E=!1;try{E=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function R(U,w){return E?new OffscreenCanvas(U,w):Ds("canvas")}function C(U,w,Y){let ne=1;const de=Et(U);if((de.width>Y||de.height>Y)&&(ne=Y/Math.max(de.width,de.height)),ne<1)if(typeof HTMLImageElement<"u"&&U instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&U instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&U instanceof ImageBitmap||typeof VideoFrame<"u"&&U instanceof VideoFrame){const se=Math.floor(ne*de.width),ze=Math.floor(ne*de.height);v===void 0&&(v=R(se,ze));const Me=w?R(se,ze):v;return Me.width=se,Me.height=ze,Me.getContext("2d").drawImage(U,0,0,se,ze),console.warn("THREE.WebGLRenderer: Texture has been resized from ("+de.width+"x"+de.height+") to ("+se+"x"+ze+")."),Me}else return"data"in U&&console.warn("THREE.WebGLRenderer: Image in DataTexture is too big ("+de.width+"x"+de.height+")."),U;return U}function y(U){return U.generateMipmaps}function m(U){r.generateMipmap(U)}function N(U){return U.isWebGLCubeRenderTarget?r.TEXTURE_CUBE_MAP:U.isWebGL3DRenderTarget?r.TEXTURE_3D:U.isWebGLArrayRenderTarget||U.isCompressedArrayTexture?r.TEXTURE_2D_ARRAY:r.TEXTURE_2D}function I(U,w,Y,ne,de=!1){if(U!==null){if(r[U]!==void 0)return r[U];console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '"+U+"'")}let se=w;if(w===r.RED&&(Y===r.FLOAT&&(se=r.R32F),Y===r.HALF_FLOAT&&(se=r.R16F),Y===r.UNSIGNED_BYTE&&(se=r.R8)),w===r.RED_INTEGER&&(Y===r.UNSIGNED_BYTE&&(se=r.R8UI),Y===r.UNSIGNED_SHORT&&(se=r.R16UI),Y===r.UNSIGNED_INT&&(se=r.R32UI),Y===r.BYTE&&(se=r.R8I),Y===r.SHORT&&(se=r.R16I),Y===r.INT&&(se=r.R32I)),w===r.RG&&(Y===r.FLOAT&&(se=r.RG32F),Y===r.HALF_FLOAT&&(se=r.RG16F),Y===r.UNSIGNED_BYTE&&(se=r.RG8)),w===r.RG_INTEGER&&(Y===r.UNSIGNED_BYTE&&(se=r.RG8UI),Y===r.UNSIGNED_SHORT&&(se=r.RG16UI),Y===r.UNSIGNED_INT&&(se=r.RG32UI),Y===r.BYTE&&(se=r.RG8I),Y===r.SHORT&&(se=r.RG16I),Y===r.INT&&(se=r.RG32I)),w===r.RGB_INTEGER&&(Y===r.UNSIGNED_BYTE&&(se=r.RGB8UI),Y===r.UNSIGNED_SHORT&&(se=r.RGB16UI),Y===r.UNSIGNED_INT&&(se=r.RGB32UI),Y===r.BYTE&&(se=r.RGB8I),Y===r.SHORT&&(se=r.RGB16I),Y===r.INT&&(se=r.RGB32I)),w===r.RGBA_INTEGER&&(Y===r.UNSIGNED_BYTE&&(se=r.RGBA8UI),Y===r.UNSIGNED_SHORT&&(se=r.RGBA16UI),Y===r.UNSIGNED_INT&&(se=r.RGBA32UI),Y===r.BYTE&&(se=r.RGBA8I),Y===r.SHORT&&(se=r.RGBA16I),Y===r.INT&&(se=r.RGBA32I)),w===r.RGB&&Y===r.UNSIGNED_INT_5_9_9_9_REV&&(se=r.RGB9_E5),w===r.RGBA){const ze=de?Cs:gt.getTransfer(ne);Y===r.FLOAT&&(se=r.RGBA32F),Y===r.HALF_FLOAT&&(se=r.RGBA16F),Y===r.UNSIGNED_BYTE&&(se=ze===bt?r.SRGB8_ALPHA8:r.RGBA8),Y===r.UNSIGNED_SHORT_4_4_4_4&&(se=r.RGBA4),Y===r.UNSIGNED_SHORT_5_5_5_1&&(se=r.RGB5_A1)}return(se===r.R16F||se===r.R32F||se===r.RG16F||se===r.RG32F||se===r.RGBA16F||se===r.RGBA32F)&&e.get("EXT_color_buffer_float"),se}function L(U,w){let Y;return U?w===null||w===Ri||w===Mr?Y=r.DEPTH24_STENCIL8:w===jn?Y=r.DEPTH32F_STENCIL8:w===Sr&&(Y=r.DEPTH24_STENCIL8,console.warn("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):w===null||w===Ri||w===Mr?Y=r.DEPTH_COMPONENT24:w===jn?Y=r.DEPTH_COMPONENT32F:w===Sr&&(Y=r.DEPTH_COMPONENT16),Y}function B(U,w){return y(U)===!0||U.isFramebufferTexture&&U.minFilter!==Tn&&U.minFilter!==Pn?Math.log2(Math.max(w.width,w.height))+1:U.mipmaps!==void 0&&U.mipmaps.length>0?U.mipmaps.length:U.isCompressedTexture&&Array.isArray(U.image)?w.mipmaps.length:1}function D(U){const w=U.target;w.removeEventListener("dispose",D),q(w),w.isVideoTexture&&_.delete(w)}function H(U){const w=U.target;w.removeEventListener("dispose",H),M(w)}function q(U){const w=n.get(U);if(w.__webglInit===void 0)return;const Y=U.source,ne=x.get(Y);if(ne){const de=ne[w.__cacheKey];de.usedTimes--,de.usedTimes===0&&P(U),Object.keys(ne).length===0&&x.delete(Y)}n.remove(U)}function P(U){const w=n.get(U);r.deleteTexture(w.__webglTexture);const Y=U.source,ne=x.get(Y);delete ne[w.__cacheKey],l.memory.textures--}function M(U){const w=n.get(U);if(U.depthTexture&&(U.depthTexture.dispose(),n.remove(U.depthTexture)),U.isWebGLCubeRenderTarget)for(let ne=0;ne<6;ne++){if(Array.isArray(w.__webglFramebuffer[ne]))for(let de=0;de<w.__webglFramebuffer[ne].length;de++)r.deleteFramebuffer(w.__webglFramebuffer[ne][de]);else r.deleteFramebuffer(w.__webglFramebuffer[ne]);w.__webglDepthbuffer&&r.deleteRenderbuffer(w.__webglDepthbuffer[ne])}else{if(Array.isArray(w.__webglFramebuffer))for(let ne=0;ne<w.__webglFramebuffer.length;ne++)r.deleteFramebuffer(w.__webglFramebuffer[ne]);else r.deleteFramebuffer(w.__webglFramebuffer);if(w.__webglDepthbuffer&&r.deleteRenderbuffer(w.__webglDepthbuffer),w.__webglMultisampledFramebuffer&&r.deleteFramebuffer(w.__webglMultisampledFramebuffer),w.__webglColorRenderbuffer)for(let ne=0;ne<w.__webglColorRenderbuffer.length;ne++)w.__webglColorRenderbuffer[ne]&&r.deleteRenderbuffer(w.__webglColorRenderbuffer[ne]);w.__webglDepthRenderbuffer&&r.deleteRenderbuffer(w.__webglDepthRenderbuffer)}const Y=U.textures;for(let ne=0,de=Y.length;ne<de;ne++){const se=n.get(Y[ne]);se.__webglTexture&&(r.deleteTexture(se.__webglTexture),l.memory.textures--),n.remove(Y[ne])}n.remove(U)}let O=0;function te(){O=0}function ee(){const U=O;return U>=a.maxTextures&&console.warn("THREE.WebGLTextures: Trying to use "+U+" texture units while this GPU supports only "+a.maxTextures),O+=1,U}function Z(U){const w=[];return w.push(U.wrapS),w.push(U.wrapT),w.push(U.wrapR||0),w.push(U.magFilter),w.push(U.minFilter),w.push(U.anisotropy),w.push(U.internalFormat),w.push(U.format),w.push(U.type),w.push(U.generateMipmaps),w.push(U.premultiplyAlpha),w.push(U.flipY),w.push(U.unpackAlignment),w.push(U.colorSpace),w.join()}function he(U,w){const Y=n.get(U);if(U.isVideoTexture&&Je(U),U.isRenderTargetTexture===!1&&U.isExternalTexture!==!0&&U.version>0&&Y.__version!==U.version){const ne=U.image;if(ne===null)console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");else if(ne.complete===!1)console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");else{Te(Y,U,w);return}}else U.isExternalTexture&&(Y.__webglTexture=U.sourceTexture?U.sourceTexture:null);t.bindTexture(r.TEXTURE_2D,Y.__webglTexture,r.TEXTURE0+w)}function ae(U,w){const Y=n.get(U);if(U.isRenderTargetTexture===!1&&U.version>0&&Y.__version!==U.version){Te(Y,U,w);return}t.bindTexture(r.TEXTURE_2D_ARRAY,Y.__webglTexture,r.TEXTURE0+w)}function Se(U,w){const Y=n.get(U);if(U.isRenderTargetTexture===!1&&U.version>0&&Y.__version!==U.version){Te(Y,U,w);return}t.bindTexture(r.TEXTURE_3D,Y.__webglTexture,r.TEXTURE0+w)}function re(U,w){const Y=n.get(U);if(U.version>0&&Y.__version!==U.version){Ee(Y,U,w);return}t.bindTexture(r.TEXTURE_CUBE_MAP,Y.__webglTexture,r.TEXTURE0+w)}const Ae={[Ja]:r.REPEAT,[wi]:r.CLAMP_TO_EDGE,[Qa]:r.MIRRORED_REPEAT},De={[Tn]:r.NEAREST,[f_]:r.NEAREST_MIPMAP_NEAREST,[Kr]:r.NEAREST_MIPMAP_LINEAR,[Pn]:r.LINEAR,[ra]:r.LINEAR_MIPMAP_NEAREST,[Ai]:r.LINEAR_MIPMAP_LINEAR},Ve={[g_]:r.NEVER,[M_]:r.ALWAYS,[v_]:r.LESS,[su]:r.LEQUAL,[x_]:r.EQUAL,[S_]:r.GEQUAL,[y_]:r.GREATER,[E_]:r.NOTEQUAL};function tt(U,w){if(w.type===jn&&e.has("OES_texture_float_linear")===!1&&(w.magFilter===Pn||w.magFilter===ra||w.magFilter===Kr||w.magFilter===Ai||w.minFilter===Pn||w.minFilter===ra||w.minFilter===Kr||w.minFilter===Ai)&&console.warn("THREE.WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),r.texParameteri(U,r.TEXTURE_WRAP_S,Ae[w.wrapS]),r.texParameteri(U,r.TEXTURE_WRAP_T,Ae[w.wrapT]),(U===r.TEXTURE_3D||U===r.TEXTURE_2D_ARRAY)&&r.texParameteri(U,r.TEXTURE_WRAP_R,Ae[w.wrapR]),r.texParameteri(U,r.TEXTURE_MAG_FILTER,De[w.magFilter]),r.texParameteri(U,r.TEXTURE_MIN_FILTER,De[w.minFilter]),w.compareFunction&&(r.texParameteri(U,r.TEXTURE_COMPARE_MODE,r.COMPARE_REF_TO_TEXTURE),r.texParameteri(U,r.TEXTURE_COMPARE_FUNC,Ve[w.compareFunction])),e.has("EXT_texture_filter_anisotropic")===!0){if(w.magFilter===Tn||w.minFilter!==Kr&&w.minFilter!==Ai||w.type===jn&&e.has("OES_texture_float_linear")===!1)return;if(w.anisotropy>1||n.get(w).__currentAnisotropy){const Y=e.get("EXT_texture_filter_anisotropic");r.texParameterf(U,Y.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(w.anisotropy,a.getMaxAnisotropy())),n.get(w).__currentAnisotropy=w.anisotropy}}}function xt(U,w){let Y=!1;U.__webglInit===void 0&&(U.__webglInit=!0,w.addEventListener("dispose",D));const ne=w.source;let de=x.get(ne);de===void 0&&(de={},x.set(ne,de));const se=Z(w);if(se!==U.__cacheKey){de[se]===void 0&&(de[se]={texture:r.createTexture(),usedTimes:0},l.memory.textures++,Y=!0),de[se].usedTimes++;const ze=de[U.__cacheKey];ze!==void 0&&(de[U.__cacheKey].usedTimes--,ze.usedTimes===0&&P(w)),U.__cacheKey=se,U.__webglTexture=de[se].texture}return Y}function Ze(U,w,Y){return Math.floor(Math.floor(U/Y)/w)}function ie(U,w,Y,ne){const se=U.updateRanges;if(se.length===0)t.texSubImage2D(r.TEXTURE_2D,0,0,0,w.width,w.height,Y,ne,w.data);else{se.sort((xe,Pe)=>xe.start-Pe.start);let ze=0;for(let xe=1;xe<se.length;xe++){const Pe=se[ze],$e=se[xe],ke=Pe.start+Pe.count,we=Ze($e.start,w.width,4),nt=Ze(Pe.start,w.width,4);$e.start<=ke+1&&we===nt&&Ze($e.start+$e.count-1,w.width,4)===we?Pe.count=Math.max(Pe.count,$e.start+$e.count-Pe.start):(++ze,se[ze]=$e)}se.length=ze+1;const Me=r.getParameter(r.UNPACK_ROW_LENGTH),Oe=r.getParameter(r.UNPACK_SKIP_PIXELS),Be=r.getParameter(r.UNPACK_SKIP_ROWS);r.pixelStorei(r.UNPACK_ROW_LENGTH,w.width);for(let xe=0,Pe=se.length;xe<Pe;xe++){const $e=se[xe],ke=Math.floor($e.start/4),we=Math.ceil($e.count/4),nt=ke%w.width,V=Math.floor(ke/w.width),ye=we,be=1;r.pixelStorei(r.UNPACK_SKIP_PIXELS,nt),r.pixelStorei(r.UNPACK_SKIP_ROWS,V),t.texSubImage2D(r.TEXTURE_2D,0,nt,V,ye,be,Y,ne,w.data)}U.clearUpdateRanges(),r.pixelStorei(r.UNPACK_ROW_LENGTH,Me),r.pixelStorei(r.UNPACK_SKIP_PIXELS,Oe),r.pixelStorei(r.UNPACK_SKIP_ROWS,Be)}}function Te(U,w,Y){let ne=r.TEXTURE_2D;(w.isDataArrayTexture||w.isCompressedArrayTexture)&&(ne=r.TEXTURE_2D_ARRAY),w.isData3DTexture&&(ne=r.TEXTURE_3D);const de=xt(U,w),se=w.source;t.bindTexture(ne,U.__webglTexture,r.TEXTURE0+Y);const ze=n.get(se);if(se.version!==ze.__version||de===!0){t.activeTexture(r.TEXTURE0+Y);const Me=gt.getPrimaries(gt.workingColorSpace),Oe=w.colorSpace===ni?null:gt.getPrimaries(w.colorSpace),Be=w.colorSpace===ni||Me===Oe?r.NONE:r.BROWSER_DEFAULT_WEBGL;r.pixelStorei(r.UNPACK_FLIP_Y_WEBGL,w.flipY),r.pixelStorei(r.UNPACK_PREMULTIPLY_ALPHA_WEBGL,w.premultiplyAlpha),r.pixelStorei(r.UNPACK_ALIGNMENT,w.unpackAlignment),r.pixelStorei(r.UNPACK_COLORSPACE_CONVERSION_WEBGL,Be);let xe=C(w.image,!1,a.maxTextureSize);xe=Pt(w,xe);const Pe=o.convert(w.format,w.colorSpace),$e=o.convert(w.type);let ke=I(w.internalFormat,Pe,$e,w.colorSpace,w.isVideoTexture);tt(ne,w);let we;const nt=w.mipmaps,V=w.isVideoTexture!==!0,ye=ze.__version===void 0||de===!0,be=se.dataReady,Ie=B(w,xe);if(w.isDepthTexture)ke=L(w.format===br,w.type),ye&&(V?t.texStorage2D(r.TEXTURE_2D,1,ke,xe.width,xe.height):t.texImage2D(r.TEXTURE_2D,0,ke,xe.width,xe.height,0,Pe,$e,null));else if(w.isDataTexture)if(nt.length>0){V&&ye&&t.texStorage2D(r.TEXTURE_2D,Ie,ke,nt[0].width,nt[0].height);for(let G=0,z=nt.length;G<z;G++)we=nt[G],V?be&&t.texSubImage2D(r.TEXTURE_2D,G,0,0,we.width,we.height,Pe,$e,we.data):t.texImage2D(r.TEXTURE_2D,G,ke,we.width,we.height,0,Pe,$e,we.data);w.generateMipmaps=!1}else V?(ye&&t.texStorage2D(r.TEXTURE_2D,Ie,ke,xe.width,xe.height),be&&ie(w,xe,Pe,$e)):t.texImage2D(r.TEXTURE_2D,0,ke,xe.width,xe.height,0,Pe,$e,xe.data);else if(w.isCompressedTexture)if(w.isCompressedArrayTexture){V&&ye&&t.texStorage3D(r.TEXTURE_2D_ARRAY,Ie,ke,nt[0].width,nt[0].height,xe.depth);for(let G=0,z=nt.length;G<z;G++)if(we=nt[G],w.format!==Mn)if(Pe!==null)if(V){if(be)if(w.layerUpdates.size>0){const Fe=gl(we.width,we.height,w.format,w.type);for(const Ke of w.layerUpdates){const pt=we.data.subarray(Ke*Fe/we.data.BYTES_PER_ELEMENT,(Ke+1)*Fe/we.data.BYTES_PER_ELEMENT);t.compressedTexSubImage3D(r.TEXTURE_2D_ARRAY,G,0,0,Ke,we.width,we.height,1,Pe,pt)}w.clearLayerUpdates()}else t.compressedTexSubImage3D(r.TEXTURE_2D_ARRAY,G,0,0,0,we.width,we.height,xe.depth,Pe,we.data)}else t.compressedTexImage3D(r.TEXTURE_2D_ARRAY,G,ke,we.width,we.height,xe.depth,0,we.data,0,0);else console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else V?be&&t.texSubImage3D(r.TEXTURE_2D_ARRAY,G,0,0,0,we.width,we.height,xe.depth,Pe,$e,we.data):t.texImage3D(r.TEXTURE_2D_ARRAY,G,ke,we.width,we.height,xe.depth,0,Pe,$e,we.data)}else{V&&ye&&t.texStorage2D(r.TEXTURE_2D,Ie,ke,nt[0].width,nt[0].height);for(let G=0,z=nt.length;G<z;G++)we=nt[G],w.format!==Mn?Pe!==null?V?be&&t.compressedTexSubImage2D(r.TEXTURE_2D,G,0,0,we.width,we.height,Pe,we.data):t.compressedTexImage2D(r.TEXTURE_2D,G,ke,we.width,we.height,0,we.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):V?be&&t.texSubImage2D(r.TEXTURE_2D,G,0,0,we.width,we.height,Pe,$e,we.data):t.texImage2D(r.TEXTURE_2D,G,ke,we.width,we.height,0,Pe,$e,we.data)}else if(w.isDataArrayTexture)if(V){if(ye&&t.texStorage3D(r.TEXTURE_2D_ARRAY,Ie,ke,xe.width,xe.height,xe.depth),be)if(w.layerUpdates.size>0){const G=gl(xe.width,xe.height,w.format,w.type);for(const z of w.layerUpdates){const Fe=xe.data.subarray(z*G/xe.data.BYTES_PER_ELEMENT,(z+1)*G/xe.data.BYTES_PER_ELEMENT);t.texSubImage3D(r.TEXTURE_2D_ARRAY,0,0,0,z,xe.width,xe.height,1,Pe,$e,Fe)}w.clearLayerUpdates()}else t.texSubImage3D(r.TEXTURE_2D_ARRAY,0,0,0,0,xe.width,xe.height,xe.depth,Pe,$e,xe.data)}else t.texImage3D(r.TEXTURE_2D_ARRAY,0,ke,xe.width,xe.height,xe.depth,0,Pe,$e,xe.data);else if(w.isData3DTexture)V?(ye&&t.texStorage3D(r.TEXTURE_3D,Ie,ke,xe.width,xe.height,xe.depth),be&&t.texSubImage3D(r.TEXTURE_3D,0,0,0,0,xe.width,xe.height,xe.depth,Pe,$e,xe.data)):t.texImage3D(r.TEXTURE_3D,0,ke,xe.width,xe.height,xe.depth,0,Pe,$e,xe.data);else if(w.isFramebufferTexture){if(ye)if(V)t.texStorage2D(r.TEXTURE_2D,Ie,ke,xe.width,xe.height);else{let G=xe.width,z=xe.height;for(let Fe=0;Fe<Ie;Fe++)t.texImage2D(r.TEXTURE_2D,Fe,ke,G,z,0,Pe,$e,null),G>>=1,z>>=1}}else if(nt.length>0){if(V&&ye){const G=Et(nt[0]);t.texStorage2D(r.TEXTURE_2D,Ie,ke,G.width,G.height)}for(let G=0,z=nt.length;G<z;G++)we=nt[G],V?be&&t.texSubImage2D(r.TEXTURE_2D,G,0,0,Pe,$e,we):t.texImage2D(r.TEXTURE_2D,G,ke,Pe,$e,we);w.generateMipmaps=!1}else if(V){if(ye){const G=Et(xe);t.texStorage2D(r.TEXTURE_2D,Ie,ke,G.width,G.height)}be&&t.texSubImage2D(r.TEXTURE_2D,0,0,0,Pe,$e,xe)}else t.texImage2D(r.TEXTURE_2D,0,ke,Pe,$e,xe);y(w)&&m(ne),ze.__version=se.version,w.onUpdate&&w.onUpdate(w)}U.__version=w.version}function Ee(U,w,Y){if(w.image.length!==6)return;const ne=xt(U,w),de=w.source;t.bindTexture(r.TEXTURE_CUBE_MAP,U.__webglTexture,r.TEXTURE0+Y);const se=n.get(de);if(de.version!==se.__version||ne===!0){t.activeTexture(r.TEXTURE0+Y);const ze=gt.getPrimaries(gt.workingColorSpace),Me=w.colorSpace===ni?null:gt.getPrimaries(w.colorSpace),Oe=w.colorSpace===ni||ze===Me?r.NONE:r.BROWSER_DEFAULT_WEBGL;r.pixelStorei(r.UNPACK_FLIP_Y_WEBGL,w.flipY),r.pixelStorei(r.UNPACK_PREMULTIPLY_ALPHA_WEBGL,w.premultiplyAlpha),r.pixelStorei(r.UNPACK_ALIGNMENT,w.unpackAlignment),r.pixelStorei(r.UNPACK_COLORSPACE_CONVERSION_WEBGL,Oe);const Be=w.isCompressedTexture||w.image[0].isCompressedTexture,xe=w.image[0]&&w.image[0].isDataTexture,Pe=[];for(let z=0;z<6;z++)!Be&&!xe?Pe[z]=C(w.image[z],!0,a.maxCubemapSize):Pe[z]=xe?w.image[z].image:w.image[z],Pe[z]=Pt(w,Pe[z]);const $e=Pe[0],ke=o.convert(w.format,w.colorSpace),we=o.convert(w.type),nt=I(w.internalFormat,ke,we,w.colorSpace),V=w.isVideoTexture!==!0,ye=se.__version===void 0||ne===!0,be=de.dataReady;let Ie=B(w,$e);tt(r.TEXTURE_CUBE_MAP,w);let G;if(Be){V&&ye&&t.texStorage2D(r.TEXTURE_CUBE_MAP,Ie,nt,$e.width,$e.height);for(let z=0;z<6;z++){G=Pe[z].mipmaps;for(let Fe=0;Fe<G.length;Fe++){const Ke=G[Fe];w.format!==Mn?ke!==null?V?be&&t.compressedTexSubImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,Fe,0,0,Ke.width,Ke.height,ke,Ke.data):t.compressedTexImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,Fe,nt,Ke.width,Ke.height,0,Ke.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):V?be&&t.texSubImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,Fe,0,0,Ke.width,Ke.height,ke,we,Ke.data):t.texImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,Fe,nt,Ke.width,Ke.height,0,ke,we,Ke.data)}}}else{if(G=w.mipmaps,V&&ye){G.length>0&&Ie++;const z=Et(Pe[0]);t.texStorage2D(r.TEXTURE_CUBE_MAP,Ie,nt,z.width,z.height)}for(let z=0;z<6;z++)if(xe){V?be&&t.texSubImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,0,0,0,Pe[z].width,Pe[z].height,ke,we,Pe[z].data):t.texImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,0,nt,Pe[z].width,Pe[z].height,0,ke,we,Pe[z].data);for(let Fe=0;Fe<G.length;Fe++){const pt=G[Fe].image[z].image;V?be&&t.texSubImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,Fe+1,0,0,pt.width,pt.height,ke,we,pt.data):t.texImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,Fe+1,nt,pt.width,pt.height,0,ke,we,pt.data)}}else{V?be&&t.texSubImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,0,0,0,ke,we,Pe[z]):t.texImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,0,nt,ke,we,Pe[z]);for(let Fe=0;Fe<G.length;Fe++){const Ke=G[Fe];V?be&&t.texSubImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,Fe+1,0,0,ke,we,Ke.image[z]):t.texImage2D(r.TEXTURE_CUBE_MAP_POSITIVE_X+z,Fe+1,nt,ke,we,Ke.image[z])}}}y(w)&&m(r.TEXTURE_CUBE_MAP),se.__version=de.version,w.onUpdate&&w.onUpdate(w)}U.__version=w.version}function ue(U,w,Y,ne,de,se){const ze=o.convert(Y.format,Y.colorSpace),Me=o.convert(Y.type),Oe=I(Y.internalFormat,ze,Me,Y.colorSpace),Be=n.get(w),xe=n.get(Y);if(xe.__renderTarget=w,!Be.__hasExternalTextures){const Pe=Math.max(1,w.width>>se),$e=Math.max(1,w.height>>se);de===r.TEXTURE_3D||de===r.TEXTURE_2D_ARRAY?t.texImage3D(de,se,Oe,Pe,$e,w.depth,0,ze,Me,null):t.texImage2D(de,se,Oe,Pe,$e,0,ze,Me,null)}t.bindFramebuffer(r.FRAMEBUFFER,U),Le(w)?u.framebufferTexture2DMultisampleEXT(r.FRAMEBUFFER,ne,de,xe.__webglTexture,0,At(w)):(de===r.TEXTURE_2D||de>=r.TEXTURE_CUBE_MAP_POSITIVE_X&&de<=r.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&r.framebufferTexture2D(r.FRAMEBUFFER,ne,de,xe.__webglTexture,se),t.bindFramebuffer(r.FRAMEBUFFER,null)}function ve(U,w,Y){if(r.bindRenderbuffer(r.RENDERBUFFER,U),w.depthBuffer){const ne=w.depthTexture,de=ne&&ne.isDepthTexture?ne.type:null,se=L(w.stencilBuffer,de),ze=w.stencilBuffer?r.DEPTH_STENCIL_ATTACHMENT:r.DEPTH_ATTACHMENT,Me=At(w);Le(w)?u.renderbufferStorageMultisampleEXT(r.RENDERBUFFER,Me,se,w.width,w.height):Y?r.renderbufferStorageMultisample(r.RENDERBUFFER,Me,se,w.width,w.height):r.renderbufferStorage(r.RENDERBUFFER,se,w.width,w.height),r.framebufferRenderbuffer(r.FRAMEBUFFER,ze,r.RENDERBUFFER,U)}else{const ne=w.textures;for(let de=0;de<ne.length;de++){const se=ne[de],ze=o.convert(se.format,se.colorSpace),Me=o.convert(se.type),Oe=I(se.internalFormat,ze,Me,se.colorSpace),Be=At(w);Y&&Le(w)===!1?r.renderbufferStorageMultisample(r.RENDERBUFFER,Be,Oe,w.width,w.height):Le(w)?u.renderbufferStorageMultisampleEXT(r.RENDERBUFFER,Be,Oe,w.width,w.height):r.renderbufferStorage(r.RENDERBUFFER,Oe,w.width,w.height)}}r.bindRenderbuffer(r.RENDERBUFFER,null)}function Ye(U,w){if(w&&w.isWebGLCubeRenderTarget)throw new Error("Depth Texture with cube render targets is not supported");if(t.bindFramebuffer(r.FRAMEBUFFER,U),!(w.depthTexture&&w.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");const ne=n.get(w.depthTexture);ne.__renderTarget=w,(!ne.__webglTexture||w.depthTexture.image.width!==w.width||w.depthTexture.image.height!==w.height)&&(w.depthTexture.image.width=w.width,w.depthTexture.image.height=w.height,w.depthTexture.needsUpdate=!0),he(w.depthTexture,0);const de=ne.__webglTexture,se=At(w);if(w.depthTexture.format===Tr)Le(w)?u.framebufferTexture2DMultisampleEXT(r.FRAMEBUFFER,r.DEPTH_ATTACHMENT,r.TEXTURE_2D,de,0,se):r.framebufferTexture2D(r.FRAMEBUFFER,r.DEPTH_ATTACHMENT,r.TEXTURE_2D,de,0);else if(w.depthTexture.format===br)Le(w)?u.framebufferTexture2DMultisampleEXT(r.FRAMEBUFFER,r.DEPTH_STENCIL_ATTACHMENT,r.TEXTURE_2D,de,0,se):r.framebufferTexture2D(r.FRAMEBUFFER,r.DEPTH_STENCIL_ATTACHMENT,r.TEXTURE_2D,de,0);else throw new Error("Unknown depthTexture format")}function Ct(U){const w=n.get(U),Y=U.isWebGLCubeRenderTarget===!0;if(w.__boundDepthTexture!==U.depthTexture){const ne=U.depthTexture;if(w.__depthDisposeCallback&&w.__depthDisposeCallback(),ne){const de=()=>{delete w.__boundDepthTexture,delete w.__depthDisposeCallback,ne.removeEventListener("dispose",de)};ne.addEventListener("dispose",de),w.__depthDisposeCallback=de}w.__boundDepthTexture=ne}if(U.depthTexture&&!w.__autoAllocateDepthBuffer){if(Y)throw new Error("target.depthTexture not supported in Cube render targets");const ne=U.texture.mipmaps;ne&&ne.length>0?Ye(w.__webglFramebuffer[0],U):Ye(w.__webglFramebuffer,U)}else if(Y){w.__webglDepthbuffer=[];for(let ne=0;ne<6;ne++)if(t.bindFramebuffer(r.FRAMEBUFFER,w.__webglFramebuffer[ne]),w.__webglDepthbuffer[ne]===void 0)w.__webglDepthbuffer[ne]=r.createRenderbuffer(),ve(w.__webglDepthbuffer[ne],U,!1);else{const de=U.stencilBuffer?r.DEPTH_STENCIL_ATTACHMENT:r.DEPTH_ATTACHMENT,se=w.__webglDepthbuffer[ne];r.bindRenderbuffer(r.RENDERBUFFER,se),r.framebufferRenderbuffer(r.FRAMEBUFFER,de,r.RENDERBUFFER,se)}}else{const ne=U.texture.mipmaps;if(ne&&ne.length>0?t.bindFramebuffer(r.FRAMEBUFFER,w.__webglFramebuffer[0]):t.bindFramebuffer(r.FRAMEBUFFER,w.__webglFramebuffer),w.__webglDepthbuffer===void 0)w.__webglDepthbuffer=r.createRenderbuffer(),ve(w.__webglDepthbuffer,U,!1);else{const de=U.stencilBuffer?r.DEPTH_STENCIL_ATTACHMENT:r.DEPTH_ATTACHMENT,se=w.__webglDepthbuffer;r.bindRenderbuffer(r.RENDERBUFFER,se),r.framebufferRenderbuffer(r.FRAMEBUFFER,de,r.RENDERBUFFER,se)}}t.bindFramebuffer(r.FRAMEBUFFER,null)}function Qe(U,w,Y){const ne=n.get(U);w!==void 0&&ue(ne.__webglFramebuffer,U,U.texture,r.COLOR_ATTACHMENT0,r.TEXTURE_2D,0),Y!==void 0&&Ct(U)}function k(U){const w=U.texture,Y=n.get(U),ne=n.get(w);U.addEventListener("dispose",H);const de=U.textures,se=U.isWebGLCubeRenderTarget===!0,ze=de.length>1;if(ze||(ne.__webglTexture===void 0&&(ne.__webglTexture=r.createTexture()),ne.__version=w.version,l.memory.textures++),se){Y.__webglFramebuffer=[];for(let Me=0;Me<6;Me++)if(w.mipmaps&&w.mipmaps.length>0){Y.__webglFramebuffer[Me]=[];for(let Oe=0;Oe<w.mipmaps.length;Oe++)Y.__webglFramebuffer[Me][Oe]=r.createFramebuffer()}else Y.__webglFramebuffer[Me]=r.createFramebuffer()}else{if(w.mipmaps&&w.mipmaps.length>0){Y.__webglFramebuffer=[];for(let Me=0;Me<w.mipmaps.length;Me++)Y.__webglFramebuffer[Me]=r.createFramebuffer()}else Y.__webglFramebuffer=r.createFramebuffer();if(ze)for(let Me=0,Oe=de.length;Me<Oe;Me++){const Be=n.get(de[Me]);Be.__webglTexture===void 0&&(Be.__webglTexture=r.createTexture(),l.memory.textures++)}if(U.samples>0&&Le(U)===!1){Y.__webglMultisampledFramebuffer=r.createFramebuffer(),Y.__webglColorRenderbuffer=[],t.bindFramebuffer(r.FRAMEBUFFER,Y.__webglMultisampledFramebuffer);for(let Me=0;Me<de.length;Me++){const Oe=de[Me];Y.__webglColorRenderbuffer[Me]=r.createRenderbuffer(),r.bindRenderbuffer(r.RENDERBUFFER,Y.__webglColorRenderbuffer[Me]);const Be=o.convert(Oe.format,Oe.colorSpace),xe=o.convert(Oe.type),Pe=I(Oe.internalFormat,Be,xe,Oe.colorSpace,U.isXRRenderTarget===!0),$e=At(U);r.renderbufferStorageMultisample(r.RENDERBUFFER,$e,Pe,U.width,U.height),r.framebufferRenderbuffer(r.FRAMEBUFFER,r.COLOR_ATTACHMENT0+Me,r.RENDERBUFFER,Y.__webglColorRenderbuffer[Me])}r.bindRenderbuffer(r.RENDERBUFFER,null),U.depthBuffer&&(Y.__webglDepthRenderbuffer=r.createRenderbuffer(),ve(Y.__webglDepthRenderbuffer,U,!0)),t.bindFramebuffer(r.FRAMEBUFFER,null)}}if(se){t.bindTexture(r.TEXTURE_CUBE_MAP,ne.__webglTexture),tt(r.TEXTURE_CUBE_MAP,w);for(let Me=0;Me<6;Me++)if(w.mipmaps&&w.mipmaps.length>0)for(let Oe=0;Oe<w.mipmaps.length;Oe++)ue(Y.__webglFramebuffer[Me][Oe],U,w,r.COLOR_ATTACHMENT0,r.TEXTURE_CUBE_MAP_POSITIVE_X+Me,Oe);else ue(Y.__webglFramebuffer[Me],U,w,r.COLOR_ATTACHMENT0,r.TEXTURE_CUBE_MAP_POSITIVE_X+Me,0);y(w)&&m(r.TEXTURE_CUBE_MAP),t.unbindTexture()}else if(ze){for(let Me=0,Oe=de.length;Me<Oe;Me++){const Be=de[Me],xe=n.get(Be);let Pe=r.TEXTURE_2D;(U.isWebGL3DRenderTarget||U.isWebGLArrayRenderTarget)&&(Pe=U.isWebGL3DRenderTarget?r.TEXTURE_3D:r.TEXTURE_2D_ARRAY),t.bindTexture(Pe,xe.__webglTexture),tt(Pe,Be),ue(Y.__webglFramebuffer,U,Be,r.COLOR_ATTACHMENT0+Me,Pe,0),y(Be)&&m(Pe)}t.unbindTexture()}else{let Me=r.TEXTURE_2D;if((U.isWebGL3DRenderTarget||U.isWebGLArrayRenderTarget)&&(Me=U.isWebGL3DRenderTarget?r.TEXTURE_3D:r.TEXTURE_2D_ARRAY),t.bindTexture(Me,ne.__webglTexture),tt(Me,w),w.mipmaps&&w.mipmaps.length>0)for(let Oe=0;Oe<w.mipmaps.length;Oe++)ue(Y.__webglFramebuffer[Oe],U,w,r.COLOR_ATTACHMENT0,Me,Oe);else ue(Y.__webglFramebuffer,U,w,r.COLOR_ATTACHMENT0,Me,0);y(w)&&m(Me),t.unbindTexture()}U.depthBuffer&&Ct(U)}function _t(U){const w=U.textures;for(let Y=0,ne=w.length;Y<ne;Y++){const de=w[Y];if(y(de)){const se=N(U),ze=n.get(de).__webglTexture;t.bindTexture(se,ze),m(se),t.unbindTexture()}}}const We=[],ft=[];function Ge(U){if(U.samples>0){if(Le(U)===!1){const w=U.textures,Y=U.width,ne=U.height;let de=r.COLOR_BUFFER_BIT;const se=U.stencilBuffer?r.DEPTH_STENCIL_ATTACHMENT:r.DEPTH_ATTACHMENT,ze=n.get(U),Me=w.length>1;if(Me)for(let Be=0;Be<w.length;Be++)t.bindFramebuffer(r.FRAMEBUFFER,ze.__webglMultisampledFramebuffer),r.framebufferRenderbuffer(r.FRAMEBUFFER,r.COLOR_ATTACHMENT0+Be,r.RENDERBUFFER,null),t.bindFramebuffer(r.FRAMEBUFFER,ze.__webglFramebuffer),r.framebufferTexture2D(r.DRAW_FRAMEBUFFER,r.COLOR_ATTACHMENT0+Be,r.TEXTURE_2D,null,0);t.bindFramebuffer(r.READ_FRAMEBUFFER,ze.__webglMultisampledFramebuffer);const Oe=U.texture.mipmaps;Oe&&Oe.length>0?t.bindFramebuffer(r.DRAW_FRAMEBUFFER,ze.__webglFramebuffer[0]):t.bindFramebuffer(r.DRAW_FRAMEBUFFER,ze.__webglFramebuffer);for(let Be=0;Be<w.length;Be++){if(U.resolveDepthBuffer&&(U.depthBuffer&&(de|=r.DEPTH_BUFFER_BIT),U.stencilBuffer&&U.resolveStencilBuffer&&(de|=r.STENCIL_BUFFER_BIT)),Me){r.framebufferRenderbuffer(r.READ_FRAMEBUFFER,r.COLOR_ATTACHMENT0,r.RENDERBUFFER,ze.__webglColorRenderbuffer[Be]);const xe=n.get(w[Be]).__webglTexture;r.framebufferTexture2D(r.DRAW_FRAMEBUFFER,r.COLOR_ATTACHMENT0,r.TEXTURE_2D,xe,0)}r.blitFramebuffer(0,0,Y,ne,0,0,Y,ne,de,r.NEAREST),p===!0&&(We.length=0,ft.length=0,We.push(r.COLOR_ATTACHMENT0+Be),U.depthBuffer&&U.resolveDepthBuffer===!1&&(We.push(se),ft.push(se),r.invalidateFramebuffer(r.DRAW_FRAMEBUFFER,ft)),r.invalidateFramebuffer(r.READ_FRAMEBUFFER,We))}if(t.bindFramebuffer(r.READ_FRAMEBUFFER,null),t.bindFramebuffer(r.DRAW_FRAMEBUFFER,null),Me)for(let Be=0;Be<w.length;Be++){t.bindFramebuffer(r.FRAMEBUFFER,ze.__webglMultisampledFramebuffer),r.framebufferRenderbuffer(r.FRAMEBUFFER,r.COLOR_ATTACHMENT0+Be,r.RENDERBUFFER,ze.__webglColorRenderbuffer[Be]);const xe=n.get(w[Be]).__webglTexture;t.bindFramebuffer(r.FRAMEBUFFER,ze.__webglFramebuffer),r.framebufferTexture2D(r.DRAW_FRAMEBUFFER,r.COLOR_ATTACHMENT0+Be,r.TEXTURE_2D,xe,0)}t.bindFramebuffer(r.DRAW_FRAMEBUFFER,ze.__webglMultisampledFramebuffer)}else if(U.depthBuffer&&U.resolveDepthBuffer===!1&&p){const w=U.stencilBuffer?r.DEPTH_STENCIL_ATTACHMENT:r.DEPTH_ATTACHMENT;r.invalidateFramebuffer(r.DRAW_FRAMEBUFFER,[w])}}}function At(U){return Math.min(a.maxSamples,U.samples)}function Le(U){const w=n.get(U);return U.samples>0&&e.has("WEBGL_multisampled_render_to_texture")===!0&&w.__useRenderToTexture!==!1}function Je(U){const w=l.render.frame;_.get(U)!==w&&(_.set(U,w),U.update())}function Pt(U,w){const Y=U.colorSpace,ne=U.format,de=U.type;return U.isCompressedTexture===!0||U.isVideoTexture===!0||Y!==rr&&Y!==ni&&(gt.getTransfer(Y)===bt?(ne!==Mn||de!==In)&&console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):console.error("THREE.WebGLTextures: Unsupported texture color space:",Y)),w}function Et(U){return typeof HTMLImageElement<"u"&&U instanceof HTMLImageElement?(f.width=U.naturalWidth||U.width,f.height=U.naturalHeight||U.height):typeof VideoFrame<"u"&&U instanceof VideoFrame?(f.width=U.displayWidth,f.height=U.displayHeight):(f.width=U.width,f.height=U.height),f}this.allocateTextureUnit=ee,this.resetTextureUnits=te,this.setTexture2D=he,this.setTexture2DArray=ae,this.setTexture3D=Se,this.setTextureCube=re,this.rebindTextures=Qe,this.setupRenderTarget=k,this.updateRenderTargetMipmap=_t,this.updateMultisampleRenderTarget=Ge,this.setupDepthRenderbuffer=Ct,this.setupFrameBufferTexture=ue,this.useMultisampledRTT=Le}function Hy(r,e){function t(n,a=ni){let o;const l=gt.getTransfer(a);if(n===In)return r.UNSIGNED_BYTE;if(n===Lo)return r.UNSIGNED_SHORT_4_4_4_4;if(n===Io)return r.UNSIGNED_SHORT_5_5_5_1;if(n===Jl)return r.UNSIGNED_INT_5_9_9_9_REV;if(n===Kl)return r.BYTE;if(n===Zl)return r.SHORT;if(n===Sr)return r.UNSIGNED_SHORT;if(n===Do)return r.INT;if(n===Ri)return r.UNSIGNED_INT;if(n===jn)return r.FLOAT;if(n===wr)return r.HALF_FLOAT;if(n===Ql)return r.ALPHA;if(n===eu)return r.RGB;if(n===Mn)return r.RGBA;if(n===Tr)return r.DEPTH_COMPONENT;if(n===br)return r.DEPTH_STENCIL;if(n===tu)return r.RED;if(n===Fo)return r.RED_INTEGER;if(n===nu)return r.RG;if(n===Uo)return r.RG_INTEGER;if(n===No)return r.RGBA_INTEGER;if(n===Ss||n===Ms||n===Ts||n===bs)if(l===bt)if(o=e.get("WEBGL_compressed_texture_s3tc_srgb"),o!==null){if(n===Ss)return o.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(n===Ms)return o.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(n===Ts)return o.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(n===bs)return o.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(o=e.get("WEBGL_compressed_texture_s3tc"),o!==null){if(n===Ss)return o.COMPRESSED_RGB_S3TC_DXT1_EXT;if(n===Ms)return o.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(n===Ts)return o.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(n===bs)return o.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(n===eo||n===to||n===no||n===io)if(o=e.get("WEBGL_compressed_texture_pvrtc"),o!==null){if(n===eo)return o.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(n===to)return o.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(n===no)return o.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(n===io)return o.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(n===ro||n===so||n===ao)if(o=e.get("WEBGL_compressed_texture_etc"),o!==null){if(n===ro||n===so)return l===bt?o.COMPRESSED_SRGB8_ETC2:o.COMPRESSED_RGB8_ETC2;if(n===ao)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:o.COMPRESSED_RGBA8_ETC2_EAC}else return null;if(n===oo||n===co||n===lo||n===uo||n===ho||n===fo||n===po||n===mo||n===_o||n===go||n===vo||n===xo||n===yo||n===Eo)if(o=e.get("WEBGL_compressed_texture_astc"),o!==null){if(n===oo)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:o.COMPRESSED_RGBA_ASTC_4x4_KHR;if(n===co)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:o.COMPRESSED_RGBA_ASTC_5x4_KHR;if(n===lo)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:o.COMPRESSED_RGBA_ASTC_5x5_KHR;if(n===uo)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:o.COMPRESSED_RGBA_ASTC_6x5_KHR;if(n===ho)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:o.COMPRESSED_RGBA_ASTC_6x6_KHR;if(n===fo)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:o.COMPRESSED_RGBA_ASTC_8x5_KHR;if(n===po)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:o.COMPRESSED_RGBA_ASTC_8x6_KHR;if(n===mo)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:o.COMPRESSED_RGBA_ASTC_8x8_KHR;if(n===_o)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:o.COMPRESSED_RGBA_ASTC_10x5_KHR;if(n===go)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:o.COMPRESSED_RGBA_ASTC_10x6_KHR;if(n===vo)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:o.COMPRESSED_RGBA_ASTC_10x8_KHR;if(n===xo)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:o.COMPRESSED_RGBA_ASTC_10x10_KHR;if(n===yo)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:o.COMPRESSED_RGBA_ASTC_12x10_KHR;if(n===Eo)return l===bt?o.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:o.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(n===ws||n===So||n===Mo)if(o=e.get("EXT_texture_compression_bptc"),o!==null){if(n===ws)return l===bt?o.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:o.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(n===So)return o.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(n===Mo)return o.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(n===iu||n===To||n===bo||n===wo)if(o=e.get("EXT_texture_compression_rgtc"),o!==null){if(n===ws)return o.COMPRESSED_RED_RGTC1_EXT;if(n===To)return o.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(n===bo)return o.COMPRESSED_RED_GREEN_RGTC2_EXT;if(n===wo)return o.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return n===Mr?r.UNSIGNED_INT_24_8:r[n]!==void 0?r[n]:null}return{convert:t}}class Mu extends on{constructor(e=null){super(),this.sourceTexture=e,this.isExternalTexture=!0}}const Vy=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,Gy=`
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`;class Wy{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(e,t){if(this.texture===null){const n=new Mu(e.texture);(e.depthNear!==t.depthNear||e.depthFar!==t.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=n}}getMesh(e){if(this.texture!==null&&this.mesh===null){const t=e.cameras[0].viewport,n=new ci({vertexShader:Vy,fragmentShader:Gy,uniforms:{depthColor:{value:this.texture},depthWidth:{value:t.z},depthHeight:{value:t.w}}});this.mesh=new _n(new Cr(20,20),n)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}}class Xy extends Li{constructor(e,t){super();const n=this;let a=null,o=1,l=null,u="local-floor",p=1,f=null,_=null,v=null,x=null,E=null,R=null;const C=new Wy,y={},m=t.getContextAttributes();let N=null,I=null;const L=[],B=[],D=new et;let H=null;const q=new mn;q.viewport=new Ut;const P=new mn;P.viewport=new Ut;const M=[q,P],O=new cg;let te=null,ee=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(ie){let Te=L[ie];return Te===void 0&&(Te=new wa,L[ie]=Te),Te.getTargetRaySpace()},this.getControllerGrip=function(ie){let Te=L[ie];return Te===void 0&&(Te=new wa,L[ie]=Te),Te.getGripSpace()},this.getHand=function(ie){let Te=L[ie];return Te===void 0&&(Te=new wa,L[ie]=Te),Te.getHandSpace()};function Z(ie){const Te=B.indexOf(ie.inputSource);if(Te===-1)return;const Ee=L[Te];Ee!==void 0&&(Ee.update(ie.inputSource,ie.frame,f||l),Ee.dispatchEvent({type:ie.type,data:ie.inputSource}))}function he(){a.removeEventListener("select",Z),a.removeEventListener("selectstart",Z),a.removeEventListener("selectend",Z),a.removeEventListener("squeeze",Z),a.removeEventListener("squeezestart",Z),a.removeEventListener("squeezeend",Z),a.removeEventListener("end",he),a.removeEventListener("inputsourceschange",ae);for(let ie=0;ie<L.length;ie++){const Te=B[ie];Te!==null&&(B[ie]=null,L[ie].disconnect(Te))}te=null,ee=null,C.reset();for(const ie in y)delete y[ie];e.setRenderTarget(N),E=null,x=null,v=null,a=null,I=null,Ze.stop(),n.isPresenting=!1,e.setPixelRatio(H),e.setSize(D.width,D.height,!1),n.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(ie){o=ie,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(ie){u=ie,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return f||l},this.setReferenceSpace=function(ie){f=ie},this.getBaseLayer=function(){return x!==null?x:E},this.getBinding=function(){return v},this.getFrame=function(){return R},this.getSession=function(){return a},this.setSession=async function(ie){if(a=ie,a!==null){if(N=e.getRenderTarget(),a.addEventListener("select",Z),a.addEventListener("selectstart",Z),a.addEventListener("selectend",Z),a.addEventListener("squeeze",Z),a.addEventListener("squeezestart",Z),a.addEventListener("squeezeend",Z),a.addEventListener("end",he),a.addEventListener("inputsourceschange",ae),m.xrCompatible!==!0&&await t.makeXRCompatible(),H=e.getPixelRatio(),e.getSize(D),typeof XRWebGLBinding<"u"&&(v=new XRWebGLBinding(a,t)),v!==null&&"createProjectionLayer"in XRWebGLBinding.prototype){let Ee=null,ue=null,ve=null;m.depth&&(ve=m.stencil?t.DEPTH24_STENCIL8:t.DEPTH_COMPONENT24,Ee=m.stencil?br:Tr,ue=m.stencil?Mr:Ri);const Ye={colorFormat:t.RGBA8,depthFormat:ve,scaleFactor:o};x=v.createProjectionLayer(Ye),a.updateRenderState({layers:[x]}),e.setPixelRatio(1),e.setSize(x.textureWidth,x.textureHeight,!1),I=new Pi(x.textureWidth,x.textureHeight,{format:Mn,type:In,depthTexture:new mu(x.textureWidth,x.textureHeight,ue,void 0,void 0,void 0,void 0,void 0,void 0,Ee),stencilBuffer:m.stencil,colorSpace:e.outputColorSpace,samples:m.antialias?4:0,resolveDepthBuffer:x.ignoreDepthValues===!1,resolveStencilBuffer:x.ignoreDepthValues===!1})}else{const Ee={antialias:m.antialias,alpha:!0,depth:m.depth,stencil:m.stencil,framebufferScaleFactor:o};E=new XRWebGLLayer(a,t,Ee),a.updateRenderState({baseLayer:E}),e.setPixelRatio(1),e.setSize(E.framebufferWidth,E.framebufferHeight,!1),I=new Pi(E.framebufferWidth,E.framebufferHeight,{format:Mn,type:In,colorSpace:e.outputColorSpace,stencilBuffer:m.stencil,resolveDepthBuffer:E.ignoreDepthValues===!1,resolveStencilBuffer:E.ignoreDepthValues===!1})}I.isXRRenderTarget=!0,this.setFoveation(p),f=null,l=await a.requestReferenceSpace(u),Ze.setContext(a),Ze.start(),n.isPresenting=!0,n.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(a!==null)return a.environmentBlendMode},this.getDepthTexture=function(){return C.getDepthTexture()};function ae(ie){for(let Te=0;Te<ie.removed.length;Te++){const Ee=ie.removed[Te],ue=B.indexOf(Ee);ue>=0&&(B[ue]=null,L[ue].disconnect(Ee))}for(let Te=0;Te<ie.added.length;Te++){const Ee=ie.added[Te];let ue=B.indexOf(Ee);if(ue===-1){for(let Ye=0;Ye<L.length;Ye++)if(Ye>=B.length){B.push(Ee),ue=Ye;break}else if(B[Ye]===null){B[Ye]=Ee,ue=Ye;break}if(ue===-1)break}const ve=L[ue];ve&&ve.connect(Ee)}}const Se=new X,re=new X;function Ae(ie,Te,Ee){Se.setFromMatrixPosition(Te.matrixWorld),re.setFromMatrixPosition(Ee.matrixWorld);const ue=Se.distanceTo(re),ve=Te.projectionMatrix.elements,Ye=Ee.projectionMatrix.elements,Ct=ve[14]/(ve[10]-1),Qe=ve[14]/(ve[10]+1),k=(ve[9]+1)/ve[5],_t=(ve[9]-1)/ve[5],We=(ve[8]-1)/ve[0],ft=(Ye[8]+1)/Ye[0],Ge=Ct*We,At=Ct*ft,Le=ue/(-We+ft),Je=Le*-We;if(Te.matrixWorld.decompose(ie.position,ie.quaternion,ie.scale),ie.translateX(Je),ie.translateZ(Le),ie.matrixWorld.compose(ie.position,ie.quaternion,ie.scale),ie.matrixWorldInverse.copy(ie.matrixWorld).invert(),ve[10]===-1)ie.projectionMatrix.copy(Te.projectionMatrix),ie.projectionMatrixInverse.copy(Te.projectionMatrixInverse);else{const Pt=Ct+Le,Et=Qe+Le,U=Ge-Je,w=At+(ue-Je),Y=k*Qe/Et*Pt,ne=_t*Qe/Et*Pt;ie.projectionMatrix.makePerspective(U,w,Y,ne,Pt,Et),ie.projectionMatrixInverse.copy(ie.projectionMatrix).invert()}}function De(ie,Te){Te===null?ie.matrixWorld.copy(ie.matrix):ie.matrixWorld.multiplyMatrices(Te.matrixWorld,ie.matrix),ie.matrixWorldInverse.copy(ie.matrixWorld).invert()}this.updateCamera=function(ie){if(a===null)return;let Te=ie.near,Ee=ie.far;C.texture!==null&&(C.depthNear>0&&(Te=C.depthNear),C.depthFar>0&&(Ee=C.depthFar)),O.near=P.near=q.near=Te,O.far=P.far=q.far=Ee,(te!==O.near||ee!==O.far)&&(a.updateRenderState({depthNear:O.near,depthFar:O.far}),te=O.near,ee=O.far),O.layers.mask=ie.layers.mask|6,q.layers.mask=O.layers.mask&3,P.layers.mask=O.layers.mask&5;const ue=ie.parent,ve=O.cameras;De(O,ue);for(let Ye=0;Ye<ve.length;Ye++)De(ve[Ye],ue);ve.length===2?Ae(O,q,P):O.projectionMatrix.copy(q.projectionMatrix),Ve(ie,O,ue)};function Ve(ie,Te,Ee){Ee===null?ie.matrix.copy(Te.matrixWorld):(ie.matrix.copy(Ee.matrixWorld),ie.matrix.invert(),ie.matrix.multiply(Te.matrixWorld)),ie.matrix.decompose(ie.position,ie.quaternion,ie.scale),ie.updateMatrixWorld(!0),ie.projectionMatrix.copy(Te.projectionMatrix),ie.projectionMatrixInverse.copy(Te.projectionMatrixInverse),ie.isPerspectiveCamera&&(ie.fov=Ao*2*Math.atan(1/ie.projectionMatrix.elements[5]),ie.zoom=1)}this.getCamera=function(){return O},this.getFoveation=function(){if(!(x===null&&E===null))return p},this.setFoveation=function(ie){p=ie,x!==null&&(x.fixedFoveation=ie),E!==null&&E.fixedFoveation!==void 0&&(E.fixedFoveation=ie)},this.hasDepthSensing=function(){return C.texture!==null},this.getDepthSensingMesh=function(){return C.getMesh(O)},this.getCameraTexture=function(ie){return y[ie]};let tt=null;function xt(ie,Te){if(_=Te.getViewerPose(f||l),R=Te,_!==null){const Ee=_.views;E!==null&&(e.setRenderTargetFramebuffer(I,E.framebuffer),e.setRenderTarget(I));let ue=!1;Ee.length!==O.cameras.length&&(O.cameras.length=0,ue=!0);for(let Qe=0;Qe<Ee.length;Qe++){const k=Ee[Qe];let _t=null;if(E!==null)_t=E.getViewport(k);else{const ft=v.getViewSubImage(x,k);_t=ft.viewport,Qe===0&&(e.setRenderTargetTextures(I,ft.colorTexture,ft.depthStencilTexture),e.setRenderTarget(I))}let We=M[Qe];We===void 0&&(We=new mn,We.layers.enable(Qe),We.viewport=new Ut,M[Qe]=We),We.matrix.fromArray(k.transform.matrix),We.matrix.decompose(We.position,We.quaternion,We.scale),We.projectionMatrix.fromArray(k.projectionMatrix),We.projectionMatrixInverse.copy(We.projectionMatrix).invert(),We.viewport.set(_t.x,_t.y,_t.width,_t.height),Qe===0&&(O.matrix.copy(We.matrix),O.matrix.decompose(O.position,O.quaternion,O.scale)),ue===!0&&O.cameras.push(We)}const ve=a.enabledFeatures;if(ve&&ve.includes("depth-sensing")&&a.depthUsage=="gpu-optimized"&&v){const Qe=v.getDepthInformation(Ee[0]);Qe&&Qe.isValid&&Qe.texture&&C.init(Qe,a.renderState)}if(ve&&ve.includes("camera-access")&&(e.state.unbindTexture(),v))for(let Qe=0;Qe<Ee.length;Qe++){const k=Ee[Qe].camera;if(k){let _t=y[k];_t||(_t=new Mu,y[k]=_t);const We=v.getCameraImage(k);_t.sourceTexture=We}}}for(let Ee=0;Ee<L.length;Ee++){const ue=B[Ee],ve=L[Ee];ue!==null&&ve!==void 0&&ve.update(ue,Te,f||l)}tt&&tt(ie,Te),Te.detectedPlanes&&n.dispatchEvent({type:"planesdetected",data:Te}),R=null}const Ze=new vu;Ze.setAnimationLoop(xt),this.setAnimationLoop=function(ie){tt=ie},this.dispose=function(){}}}const Si=new Fn,jy=new Ft;function $y(r,e){function t(y,m){y.matrixAutoUpdate===!0&&y.updateMatrix(),m.value.copy(y.matrix)}function n(y,m){m.color.getRGB(y.fogColor.value,hu(r)),m.isFog?(y.fogNear.value=m.near,y.fogFar.value=m.far):m.isFogExp2&&(y.fogDensity.value=m.density)}function a(y,m,N,I,L){m.isMeshBasicMaterial||m.isMeshLambertMaterial?o(y,m):m.isMeshToonMaterial?(o(y,m),v(y,m)):m.isMeshPhongMaterial?(o(y,m),_(y,m)):m.isMeshStandardMaterial?(o(y,m),x(y,m),m.isMeshPhysicalMaterial&&E(y,m,L)):m.isMeshMatcapMaterial?(o(y,m),R(y,m)):m.isMeshDepthMaterial?o(y,m):m.isMeshDistanceMaterial?(o(y,m),C(y,m)):m.isMeshNormalMaterial?o(y,m):m.isLineBasicMaterial?(l(y,m),m.isLineDashedMaterial&&u(y,m)):m.isPointsMaterial?p(y,m,N,I):m.isSpriteMaterial?f(y,m):m.isShadowMaterial?(y.color.value.copy(m.color),y.opacity.value=m.opacity):m.isShaderMaterial&&(m.uniformsNeedUpdate=!1)}function o(y,m){y.opacity.value=m.opacity,m.color&&y.diffuse.value.copy(m.color),m.emissive&&y.emissive.value.copy(m.emissive).multiplyScalar(m.emissiveIntensity),m.map&&(y.map.value=m.map,t(m.map,y.mapTransform)),m.alphaMap&&(y.alphaMap.value=m.alphaMap,t(m.alphaMap,y.alphaMapTransform)),m.bumpMap&&(y.bumpMap.value=m.bumpMap,t(m.bumpMap,y.bumpMapTransform),y.bumpScale.value=m.bumpScale,m.side===an&&(y.bumpScale.value*=-1)),m.normalMap&&(y.normalMap.value=m.normalMap,t(m.normalMap,y.normalMapTransform),y.normalScale.value.copy(m.normalScale),m.side===an&&y.normalScale.value.negate()),m.displacementMap&&(y.displacementMap.value=m.displacementMap,t(m.displacementMap,y.displacementMapTransform),y.displacementScale.value=m.displacementScale,y.displacementBias.value=m.displacementBias),m.emissiveMap&&(y.emissiveMap.value=m.emissiveMap,t(m.emissiveMap,y.emissiveMapTransform)),m.specularMap&&(y.specularMap.value=m.specularMap,t(m.specularMap,y.specularMapTransform)),m.alphaTest>0&&(y.alphaTest.value=m.alphaTest);const N=e.get(m),I=N.envMap,L=N.envMapRotation;I&&(y.envMap.value=I,Si.copy(L),Si.x*=-1,Si.y*=-1,Si.z*=-1,I.isCubeTexture&&I.isRenderTargetTexture===!1&&(Si.y*=-1,Si.z*=-1),y.envMapRotation.value.setFromMatrix4(jy.makeRotationFromEuler(Si)),y.flipEnvMap.value=I.isCubeTexture&&I.isRenderTargetTexture===!1?-1:1,y.reflectivity.value=m.reflectivity,y.ior.value=m.ior,y.refractionRatio.value=m.refractionRatio),m.lightMap&&(y.lightMap.value=m.lightMap,y.lightMapIntensity.value=m.lightMapIntensity,t(m.lightMap,y.lightMapTransform)),m.aoMap&&(y.aoMap.value=m.aoMap,y.aoMapIntensity.value=m.aoMapIntensity,t(m.aoMap,y.aoMapTransform))}function l(y,m){y.diffuse.value.copy(m.color),y.opacity.value=m.opacity,m.map&&(y.map.value=m.map,t(m.map,y.mapTransform))}function u(y,m){y.dashSize.value=m.dashSize,y.totalSize.value=m.dashSize+m.gapSize,y.scale.value=m.scale}function p(y,m,N,I){y.diffuse.value.copy(m.color),y.opacity.value=m.opacity,y.size.value=m.size*N,y.scale.value=I*.5,m.map&&(y.map.value=m.map,t(m.map,y.uvTransform)),m.alphaMap&&(y.alphaMap.value=m.alphaMap,t(m.alphaMap,y.alphaMapTransform)),m.alphaTest>0&&(y.alphaTest.value=m.alphaTest)}function f(y,m){y.diffuse.value.copy(m.color),y.opacity.value=m.opacity,y.rotation.value=m.rotation,m.map&&(y.map.value=m.map,t(m.map,y.mapTransform)),m.alphaMap&&(y.alphaMap.value=m.alphaMap,t(m.alphaMap,y.alphaMapTransform)),m.alphaTest>0&&(y.alphaTest.value=m.alphaTest)}function _(y,m){y.specular.value.copy(m.specular),y.shininess.value=Math.max(m.shininess,1e-4)}function v(y,m){m.gradientMap&&(y.gradientMap.value=m.gradientMap)}function x(y,m){y.metalness.value=m.metalness,m.metalnessMap&&(y.metalnessMap.value=m.metalnessMap,t(m.metalnessMap,y.metalnessMapTransform)),y.roughness.value=m.roughness,m.roughnessMap&&(y.roughnessMap.value=m.roughnessMap,t(m.roughnessMap,y.roughnessMapTransform)),m.envMap&&(y.envMapIntensity.value=m.envMapIntensity)}function E(y,m,N){y.ior.value=m.ior,m.sheen>0&&(y.sheenColor.value.copy(m.sheenColor).multiplyScalar(m.sheen),y.sheenRoughness.value=m.sheenRoughness,m.sheenColorMap&&(y.sheenColorMap.value=m.sheenColorMap,t(m.sheenColorMap,y.sheenColorMapTransform)),m.sheenRoughnessMap&&(y.sheenRoughnessMap.value=m.sheenRoughnessMap,t(m.sheenRoughnessMap,y.sheenRoughnessMapTransform))),m.clearcoat>0&&(y.clearcoat.value=m.clearcoat,y.clearcoatRoughness.value=m.clearcoatRoughness,m.clearcoatMap&&(y.clearcoatMap.value=m.clearcoatMap,t(m.clearcoatMap,y.clearcoatMapTransform)),m.clearcoatRoughnessMap&&(y.clearcoatRoughnessMap.value=m.clearcoatRoughnessMap,t(m.clearcoatRoughnessMap,y.clearcoatRoughnessMapTransform)),m.clearcoatNormalMap&&(y.clearcoatNormalMap.value=m.clearcoatNormalMap,t(m.clearcoatNormalMap,y.clearcoatNormalMapTransform),y.clearcoatNormalScale.value.copy(m.clearcoatNormalScale),m.side===an&&y.clearcoatNormalScale.value.negate())),m.dispersion>0&&(y.dispersion.value=m.dispersion),m.iridescence>0&&(y.iridescence.value=m.iridescence,y.iridescenceIOR.value=m.iridescenceIOR,y.iridescenceThicknessMinimum.value=m.iridescenceThicknessRange[0],y.iridescenceThicknessMaximum.value=m.iridescenceThicknessRange[1],m.iridescenceMap&&(y.iridescenceMap.value=m.iridescenceMap,t(m.iridescenceMap,y.iridescenceMapTransform)),m.iridescenceThicknessMap&&(y.iridescenceThicknessMap.value=m.iridescenceThicknessMap,t(m.iridescenceThicknessMap,y.iridescenceThicknessMapTransform))),m.transmission>0&&(y.transmission.value=m.transmission,y.transmissionSamplerMap.value=N.texture,y.transmissionSamplerSize.value.set(N.width,N.height),m.transmissionMap&&(y.transmissionMap.value=m.transmissionMap,t(m.transmissionMap,y.transmissionMapTransform)),y.thickness.value=m.thickness,m.thicknessMap&&(y.thicknessMap.value=m.thicknessMap,t(m.thicknessMap,y.thicknessMapTransform)),y.attenuationDistance.value=m.attenuationDistance,y.attenuationColor.value.copy(m.attenuationColor)),m.anisotropy>0&&(y.anisotropyVector.value.set(m.anisotropy*Math.cos(m.anisotropyRotation),m.anisotropy*Math.sin(m.anisotropyRotation)),m.anisotropyMap&&(y.anisotropyMap.value=m.anisotropyMap,t(m.anisotropyMap,y.anisotropyMapTransform))),y.specularIntensity.value=m.specularIntensity,y.specularColor.value.copy(m.specularColor),m.specularColorMap&&(y.specularColorMap.value=m.specularColorMap,t(m.specularColorMap,y.specularColorMapTransform)),m.specularIntensityMap&&(y.specularIntensityMap.value=m.specularIntensityMap,t(m.specularIntensityMap,y.specularIntensityMapTransform))}function R(y,m){m.matcap&&(y.matcap.value=m.matcap)}function C(y,m){const N=e.get(m).light;y.referencePosition.value.setFromMatrixPosition(N.matrixWorld),y.nearDistance.value=N.shadow.camera.near,y.farDistance.value=N.shadow.camera.far}return{refreshFogUniforms:n,refreshMaterialUniforms:a}}function qy(r,e,t,n){let a={},o={},l=[];const u=r.getParameter(r.MAX_UNIFORM_BUFFER_BINDINGS);function p(N,I){const L=I.program;n.uniformBlockBinding(N,L)}function f(N,I){let L=a[N.id];L===void 0&&(R(N),L=_(N),a[N.id]=L,N.addEventListener("dispose",y));const B=I.program;n.updateUBOMapping(N,B);const D=e.render.frame;o[N.id]!==D&&(x(N),o[N.id]=D)}function _(N){const I=v();N.__bindingPointIndex=I;const L=r.createBuffer(),B=N.__size,D=N.usage;return r.bindBuffer(r.UNIFORM_BUFFER,L),r.bufferData(r.UNIFORM_BUFFER,B,D),r.bindBuffer(r.UNIFORM_BUFFER,null),r.bindBufferBase(r.UNIFORM_BUFFER,I,L),L}function v(){for(let N=0;N<u;N++)if(l.indexOf(N)===-1)return l.push(N),N;return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function x(N){const I=a[N.id],L=N.uniforms,B=N.__cache;r.bindBuffer(r.UNIFORM_BUFFER,I);for(let D=0,H=L.length;D<H;D++){const q=Array.isArray(L[D])?L[D]:[L[D]];for(let P=0,M=q.length;P<M;P++){const O=q[P];if(E(O,D,P,B)===!0){const te=O.__offset,ee=Array.isArray(O.value)?O.value:[O.value];let Z=0;for(let he=0;he<ee.length;he++){const ae=ee[he],Se=C(ae);typeof ae=="number"||typeof ae=="boolean"?(O.__data[0]=ae,r.bufferSubData(r.UNIFORM_BUFFER,te+Z,O.__data)):ae.isMatrix3?(O.__data[0]=ae.elements[0],O.__data[1]=ae.elements[1],O.__data[2]=ae.elements[2],O.__data[3]=0,O.__data[4]=ae.elements[3],O.__data[5]=ae.elements[4],O.__data[6]=ae.elements[5],O.__data[7]=0,O.__data[8]=ae.elements[6],O.__data[9]=ae.elements[7],O.__data[10]=ae.elements[8],O.__data[11]=0):(ae.toArray(O.__data,Z),Z+=Se.storage/Float32Array.BYTES_PER_ELEMENT)}r.bufferSubData(r.UNIFORM_BUFFER,te,O.__data)}}}r.bindBuffer(r.UNIFORM_BUFFER,null)}function E(N,I,L,B){const D=N.value,H=I+"_"+L;if(B[H]===void 0)return typeof D=="number"||typeof D=="boolean"?B[H]=D:B[H]=D.clone(),!0;{const q=B[H];if(typeof D=="number"||typeof D=="boolean"){if(q!==D)return B[H]=D,!0}else if(q.equals(D)===!1)return q.copy(D),!0}return!1}function R(N){const I=N.uniforms;let L=0;const B=16;for(let H=0,q=I.length;H<q;H++){const P=Array.isArray(I[H])?I[H]:[I[H]];for(let M=0,O=P.length;M<O;M++){const te=P[M],ee=Array.isArray(te.value)?te.value:[te.value];for(let Z=0,he=ee.length;Z<he;Z++){const ae=ee[Z],Se=C(ae),re=L%B,Ae=re%Se.boundary,De=re+Ae;L+=Ae,De!==0&&B-De<Se.storage&&(L+=B-De),te.__data=new Float32Array(Se.storage/Float32Array.BYTES_PER_ELEMENT),te.__offset=L,L+=Se.storage}}}const D=L%B;return D>0&&(L+=B-D),N.__size=L,N.__cache={},this}function C(N){const I={boundary:0,storage:0};return typeof N=="number"||typeof N=="boolean"?(I.boundary=4,I.storage=4):N.isVector2?(I.boundary=8,I.storage=8):N.isVector3||N.isColor?(I.boundary=16,I.storage=12):N.isVector4?(I.boundary=16,I.storage=16):N.isMatrix3?(I.boundary=48,I.storage=48):N.isMatrix4?(I.boundary=64,I.storage=64):N.isTexture?console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group."):console.warn("THREE.WebGLRenderer: Unsupported uniform value type.",N),I}function y(N){const I=N.target;I.removeEventListener("dispose",y);const L=l.indexOf(I.__bindingPointIndex);l.splice(L,1),r.deleteBuffer(a[I.id]),delete a[I.id],delete o[I.id]}function m(){for(const N in a)r.deleteBuffer(a[N]);l=[],a={},o={}}return{bind:p,update:f,dispose:m}}class Yy{constructor(e={}){const{canvas:t=w_(),context:n=null,depth:a=!0,stencil:o=!1,alpha:l=!1,antialias:u=!1,premultipliedAlpha:p=!0,preserveDrawingBuffer:f=!1,powerPreference:_="default",failIfMajorPerformanceCaveat:v=!1,reversedDepthBuffer:x=!1}=e;this.isWebGLRenderer=!0;let E;if(n!==null){if(typeof WebGLRenderingContext<"u"&&n instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");E=n.getContextAttributes().alpha}else E=l;const R=new Uint32Array(4),C=new Int32Array(4);let y=null,m=null;const N=[],I=[];this.domElement=t,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this.toneMapping=ai,this.toneMappingExposure=1,this.transmissionResolutionScale=1;const L=this;let B=!1;this._outputColorSpace=hn;let D=0,H=0,q=null,P=-1,M=null;const O=new Ut,te=new Ut;let ee=null;const Z=new ot(0);let he=0,ae=t.width,Se=t.height,re=1,Ae=null,De=null;const Ve=new Ut(0,0,ae,Se),tt=new Ut(0,0,ae,Se);let xt=!1;const Ze=new Ho;let ie=!1,Te=!1;const Ee=new Ft,ue=new X,ve=new Ut,Ye={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0};let Ct=!1;function Qe(){return q===null?re:1}let k=n;function _t(A,j){return t.getContext(A,j)}try{const A={alpha:!0,depth:a,stencil:o,antialias:u,premultipliedAlpha:p,preserveDrawingBuffer:f,powerPreference:_,failIfMajorPerformanceCaveat:v};if("setAttribute"in t&&t.setAttribute("data-engine","three.js r179"),t.addEventListener("webglcontextlost",be,!1),t.addEventListener("webglcontextrestored",Ie,!1),t.addEventListener("webglcontextcreationerror",G,!1),k===null){const j="webgl2";if(k=_t(j,A),k===null)throw _t(j)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}}catch(A){throw console.error("THREE.WebGLRenderer: "+A.message),A}let We,ft,Ge,At,Le,Je,Pt,Et,U,w,Y,ne,de,se,ze,Me,Oe,Be,xe,Pe,$e,ke,we,nt;function V(){We=new sx(k),We.init(),ke=new Hy(k,We),ft=new J0(k,We,e,ke),Ge=new By(k,We),ft.reversedDepthBuffer&&x&&Ge.buffers.depth.setReversed(!0),At=new cx(k),Le=new wy,Je=new zy(k,We,Ge,Le,ft,ke,At),Pt=new ex(L),Et=new rx(L),U=new pg(k),we=new K0(k,U),w=new ax(k,U,At,we),Y=new ux(k,w,U,At),xe=new lx(k,ft,Je),Me=new Q0(Le),ne=new by(L,Pt,Et,We,ft,we,Me),de=new $y(L,Le),se=new Ry,ze=new Fy(We),Be=new Y0(L,Pt,Et,Ge,Y,E,p),Oe=new Oy(L,Y,ft),nt=new qy(k,At,ft,Ge),Pe=new Z0(k,We,At),$e=new ox(k,We,At),At.programs=ne.programs,L.capabilities=ft,L.extensions=We,L.properties=Le,L.renderLists=se,L.shadowMap=Oe,L.state=Ge,L.info=At}V();const ye=new Xy(L,k);this.xr=ye,this.getContext=function(){return k},this.getContextAttributes=function(){return k.getContextAttributes()},this.forceContextLoss=function(){const A=We.get("WEBGL_lose_context");A&&A.loseContext()},this.forceContextRestore=function(){const A=We.get("WEBGL_lose_context");A&&A.restoreContext()},this.getPixelRatio=function(){return re},this.setPixelRatio=function(A){A!==void 0&&(re=A,this.setSize(ae,Se,!1))},this.getSize=function(A){return A.set(ae,Se)},this.setSize=function(A,j,Q=!0){if(ye.isPresenting){console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");return}ae=A,Se=j,t.width=Math.floor(A*re),t.height=Math.floor(j*re),Q===!0&&(t.style.width=A+"px",t.style.height=j+"px"),this.setViewport(0,0,A,j)},this.getDrawingBufferSize=function(A){return A.set(ae*re,Se*re).floor()},this.setDrawingBufferSize=function(A,j,Q){ae=A,Se=j,re=Q,t.width=Math.floor(A*Q),t.height=Math.floor(j*Q),this.setViewport(0,0,A,j)},this.getCurrentViewport=function(A){return A.copy(O)},this.getViewport=function(A){return A.copy(Ve)},this.setViewport=function(A,j,Q,J){A.isVector4?Ve.set(A.x,A.y,A.z,A.w):Ve.set(A,j,Q,J),Ge.viewport(O.copy(Ve).multiplyScalar(re).round())},this.getScissor=function(A){return A.copy(tt)},this.setScissor=function(A,j,Q,J){A.isVector4?tt.set(A.x,A.y,A.z,A.w):tt.set(A,j,Q,J),Ge.scissor(te.copy(tt).multiplyScalar(re).round())},this.getScissorTest=function(){return xt},this.setScissorTest=function(A){Ge.setScissorTest(xt=A)},this.setOpaqueSort=function(A){Ae=A},this.setTransparentSort=function(A){De=A},this.getClearColor=function(A){return A.copy(Be.getClearColor())},this.setClearColor=function(){Be.setClearColor(...arguments)},this.getClearAlpha=function(){return Be.getClearAlpha()},this.setClearAlpha=function(){Be.setClearAlpha(...arguments)},this.clear=function(A=!0,j=!0,Q=!0){let J=0;if(A){let $=!1;if(q!==null){const pe=q.texture.format;$=pe===No||pe===Uo||pe===Fo}if($){const pe=q.texture.type,Re=pe===In||pe===Ri||pe===Sr||pe===Mr||pe===Lo||pe===Io,Ne=Be.getClearColor(),Ue=Be.getClearAlpha(),He=Ne.r,qe=Ne.g,_e=Ne.b;Re?(R[0]=He,R[1]=qe,R[2]=_e,R[3]=Ue,k.clearBufferuiv(k.COLOR,0,R)):(C[0]=He,C[1]=qe,C[2]=_e,C[3]=Ue,k.clearBufferiv(k.COLOR,0,C))}else J|=k.COLOR_BUFFER_BIT}j&&(J|=k.DEPTH_BUFFER_BIT),Q&&(J|=k.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),k.clear(J)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){t.removeEventListener("webglcontextlost",be,!1),t.removeEventListener("webglcontextrestored",Ie,!1),t.removeEventListener("webglcontextcreationerror",G,!1),Be.dispose(),se.dispose(),ze.dispose(),Le.dispose(),Pt.dispose(),Et.dispose(),Y.dispose(),we.dispose(),nt.dispose(),ne.dispose(),ye.dispose(),ye.removeEventListener("sessionstart",Ot),ye.removeEventListener("sessionend",li),Un.stop()};function be(A){A.preventDefault(),console.log("THREE.WebGLRenderer: Context Lost."),B=!0}function Ie(){console.log("THREE.WebGLRenderer: Context Restored."),B=!1;const A=At.autoReset,j=Oe.enabled,Q=Oe.autoUpdate,J=Oe.needsUpdate,$=Oe.type;V(),At.autoReset=A,Oe.enabled=j,Oe.autoUpdate=Q,Oe.needsUpdate=J,Oe.type=$}function G(A){console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ",A.statusMessage)}function z(A){const j=A.target;j.removeEventListener("dispose",z),Fe(j)}function Fe(A){Ke(A),Le.remove(A)}function Ke(A){const j=Le.get(A).programs;j!==void 0&&(j.forEach(function(Q){ne.releaseProgram(Q)}),A.isShaderMaterial&&ne.releaseShaderCache(A))}this.renderBufferDirect=function(A,j,Q,J,$,pe){j===null&&(j=Ye);const Re=$.isMesh&&$.matrixWorld.determinant()<0,Ne=Bs(A,j,Q,J,$);Ge.setMaterial(J,Re);let Ue=Q.index,He=1;if(J.wireframe===!0){if(Ue=w.getWireframeAttribute(Q),Ue===void 0)return;He=2}const qe=Q.drawRange,_e=Q.attributes.position;let ct=qe.start*He,vt=(qe.start+qe.count)*He;pe!==null&&(ct=Math.max(ct,pe.start*He),vt=Math.min(vt,(pe.start+pe.count)*He)),Ue!==null?(ct=Math.max(ct,0),vt=Math.min(vt,Ue.count)):_e!=null&&(ct=Math.max(ct,0),vt=Math.min(vt,_e.count));const It=vt-ct;if(It<0||It===1/0)return;we.setup($,J,Ne,Q,Ue);let Mt,St=Pe;if(Ue!==null&&(Mt=U.get(Ue),St=$e,St.setIndex(Mt)),$.isMesh)J.wireframe===!0?(Ge.setLineWidth(J.wireframeLinewidth*Qe()),St.setMode(k.LINES)):St.setMode(k.TRIANGLES);else if($.isLine){let Xe=J.linewidth;Xe===void 0&&(Xe=1),Ge.setLineWidth(Xe*Qe()),$.isLineSegments?St.setMode(k.LINES):$.isLineLoop?St.setMode(k.LINE_LOOP):St.setMode(k.LINE_STRIP)}else $.isPoints?St.setMode(k.POINTS):$.isSprite&&St.setMode(k.TRIANGLES);if($.isBatchedMesh)if($._multiDrawInstances!==null)Qi("THREE.WebGLRenderer: renderMultiDrawInstances has been deprecated and will be removed in r184. Append to renderMultiDraw arguments and use indirection."),St.renderMultiDrawInstances($._multiDrawStarts,$._multiDrawCounts,$._multiDrawCount,$._multiDrawInstances);else if(We.get("WEBGL_multi_draw"))St.renderMultiDraw($._multiDrawStarts,$._multiDrawCounts,$._multiDrawCount);else{const Xe=$._multiDrawStarts,Dt=$._multiDrawCounts,ut=$._multiDrawCount,en=Ue?U.get(Ue).bytesPerElement:1,On=Le.get(J).currentProgram.getUniforms();for(let S=0;S<ut;S++)On.setValue(k,"_gl_DrawID",S),St.render(Xe[S]/en,Dt[S])}else if($.isInstancedMesh)St.renderInstances(ct,It,$.count);else if(Q.isInstancedBufferGeometry){const Xe=Q._maxInstanceCount!==void 0?Q._maxInstanceCount:1/0,Dt=Math.min(Q.instanceCount,Xe);St.renderInstances(ct,It,Dt)}else St.render(ct,It)};function pt(A,j,Q){A.transparent===!0&&A.side===Xn&&A.forceSinglePass===!1?(A.side=an,A.needsUpdate=!0,qn(A,j,Q),A.side=oi,A.needsUpdate=!0,qn(A,j,Q),A.side=Xn):qn(A,j,Q)}this.compile=function(A,j,Q=null){Q===null&&(Q=A),m=ze.get(Q),m.init(j),I.push(m),Q.traverseVisible(function($){$.isLight&&$.layers.test(j.layers)&&(m.pushLight($),$.castShadow&&m.pushShadow($))}),A!==Q&&A.traverseVisible(function($){$.isLight&&$.layers.test(j.layers)&&(m.pushLight($),$.castShadow&&m.pushShadow($))}),m.setupLights();const J=new Set;return A.traverse(function($){if(!($.isMesh||$.isPoints||$.isLine||$.isSprite))return;const pe=$.material;if(pe)if(Array.isArray(pe))for(let Re=0;Re<pe.length;Re++){const Ne=pe[Re];pt(Ne,Q,$),J.add(Ne)}else pt(pe,Q,$),J.add(pe)}),m=I.pop(),J},this.compileAsync=function(A,j,Q=null){const J=this.compile(A,j,Q);return new Promise($=>{function pe(){if(J.forEach(function(Re){Le.get(Re).currentProgram.isReady()&&J.delete(Re)}),J.size===0){$(A);return}setTimeout(pe,10)}We.get("KHR_parallel_shader_compile")!==null?pe():setTimeout(pe,10)})};let rt=null;function gn(A){rt&&rt(A)}function Ot(){Un.stop()}function li(){Un.start()}const Un=new vu;Un.setAnimationLoop(gn),typeof self<"u"&&Un.setContext(self),this.setAnimationLoop=function(A){rt=A,ye.setAnimationLoop(A),A===null?Un.stop():Un.start()},ye.addEventListener("sessionstart",Ot),ye.addEventListener("sessionend",li),this.render=function(A,j){if(j!==void 0&&j.isCamera!==!0){console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(B===!0)return;if(A.matrixWorldAutoUpdate===!0&&A.updateMatrixWorld(),j.parent===null&&j.matrixWorldAutoUpdate===!0&&j.updateMatrixWorld(),ye.enabled===!0&&ye.isPresenting===!0&&(ye.cameraAutoUpdate===!0&&ye.updateCamera(j),j=ye.getCamera()),A.isScene===!0&&A.onBeforeRender(L,A,j,q),m=ze.get(A,I.length),m.init(j),I.push(m),Ee.multiplyMatrices(j.projectionMatrix,j.matrixWorldInverse),Ze.setFromProjectionMatrix(Ee,Dn,j.reversedDepth),Te=this.localClippingEnabled,ie=Me.init(this.clippingPlanes,Te),y=se.get(A,N.length),y.init(),N.push(y),ye.enabled===!0&&ye.isPresenting===!0){const pe=L.xr.getDepthSensingMesh();pe!==null&&cr(pe,j,-1/0,L.sortObjects)}cr(A,j,0,L.sortObjects),y.finish(),L.sortObjects===!0&&y.sort(Ae,De),Ct=ye.enabled===!1||ye.isPresenting===!1||ye.hasDepthSensing()===!1,Ct&&Be.addToRenderList(y,A),this.info.render.frame++,ie===!0&&Me.beginShadows();const Q=m.state.shadowsArray;Oe.render(Q,A,j),ie===!0&&Me.endShadows(),this.info.autoReset===!0&&this.info.reset();const J=y.opaque,$=y.transmissive;if(m.setupLights(),j.isArrayCamera){const pe=j.cameras;if($.length>0)for(let Re=0,Ne=pe.length;Re<Ne;Re++){const Ue=pe[Re];Pr(J,$,A,Ue)}Ct&&Be.render(A);for(let Re=0,Ne=pe.length;Re<Ne;Re++){const Ue=pe[Re];dn(y,A,Ue,Ue.viewport)}}else $.length>0&&Pr(J,$,A,j),Ct&&Be.render(A),dn(y,A,j);q!==null&&H===0&&(Je.updateMultisampleRenderTarget(q),Je.updateRenderTargetMipmap(q)),A.isScene===!0&&A.onAfterRender(L,A,j),we.resetDefaultState(),P=-1,M=null,I.pop(),I.length>0?(m=I[I.length-1],ie===!0&&Me.setGlobalState(L.clippingPlanes,m.state.camera)):m=null,N.pop(),N.length>0?y=N[N.length-1]:y=null};function cr(A,j,Q,J){if(A.visible===!1)return;if(A.layers.test(j.layers)){if(A.isGroup)Q=A.renderOrder;else if(A.isLOD)A.autoUpdate===!0&&A.update(j);else if(A.isLight)m.pushLight(A),A.castShadow&&m.pushShadow(A);else if(A.isSprite){if(!A.frustumCulled||Ze.intersectsSprite(A)){J&&ve.setFromMatrixPosition(A.matrixWorld).applyMatrix4(Ee);const Re=Y.update(A),Ne=A.material;Ne.visible&&y.push(A,Re,Ne,Q,ve.z,null)}}else if((A.isMesh||A.isLine||A.isPoints)&&(!A.frustumCulled||Ze.intersectsObject(A))){const Re=Y.update(A),Ne=A.material;if(J&&(A.boundingSphere!==void 0?(A.boundingSphere===null&&A.computeBoundingSphere(),ve.copy(A.boundingSphere.center)):(Re.boundingSphere===null&&Re.computeBoundingSphere(),ve.copy(Re.boundingSphere.center)),ve.applyMatrix4(A.matrixWorld).applyMatrix4(Ee)),Array.isArray(Ne)){const Ue=Re.groups;for(let He=0,qe=Ue.length;He<qe;He++){const _e=Ue[He],ct=Ne[_e.materialIndex];ct&&ct.visible&&y.push(A,Re,ct,Q,ve.z,_e)}}else Ne.visible&&y.push(A,Re,Ne,Q,ve.z,null)}}const pe=A.children;for(let Re=0,Ne=pe.length;Re<Ne;Re++)cr(pe[Re],j,Q,J)}function dn(A,j,Q,J){const $=A.opaque,pe=A.transmissive,Re=A.transparent;m.setupLightsView(Q),ie===!0&&Me.setGlobalState(L.clippingPlanes,Q),J&&Ge.viewport(O.copy(J)),$.length>0&&Nn($,j,Q),pe.length>0&&Nn(pe,j,Q),Re.length>0&&Nn(Re,j,Q),Ge.buffers.depth.setTest(!0),Ge.buffers.depth.setMask(!0),Ge.buffers.color.setMask(!0),Ge.setPolygonOffset(!1)}function Pr(A,j,Q,J){if((Q.isScene===!0?Q.overrideMaterial:null)!==null)return;m.state.transmissionRenderTarget[J.id]===void 0&&(m.state.transmissionRenderTarget[J.id]=new Pi(1,1,{generateMipmaps:!0,type:We.has("EXT_color_buffer_half_float")||We.has("EXT_color_buffer_float")?wr:In,minFilter:Ai,samples:4,stencilBuffer:o,resolveDepthBuffer:!1,resolveStencilBuffer:!1,colorSpace:gt.workingColorSpace}));const pe=m.state.transmissionRenderTarget[J.id],Re=J.viewport||O;pe.setSize(Re.z*L.transmissionResolutionScale,Re.w*L.transmissionResolutionScale);const Ne=L.getRenderTarget(),Ue=L.getActiveCubeFace(),He=L.getActiveMipmapLevel();L.setRenderTarget(pe),L.getClearColor(Z),he=L.getClearAlpha(),he<1&&L.setClearColor(16777215,.5),L.clear(),Ct&&Be.render(Q);const qe=L.toneMapping;L.toneMapping=ai;const _e=J.viewport;if(J.viewport!==void 0&&(J.viewport=void 0),m.setupLightsView(J),ie===!0&&Me.setGlobalState(L.clippingPlanes,J),Nn(A,Q,J),Je.updateMultisampleRenderTarget(pe),Je.updateRenderTargetMipmap(pe),We.has("WEBGL_multisampled_render_to_texture")===!1){let ct=!1;for(let vt=0,It=j.length;vt<It;vt++){const Mt=j[vt],St=Mt.object,Xe=Mt.geometry,Dt=Mt.material,ut=Mt.group;if(Dt.side===Xn&&St.layers.test(J.layers)){const en=Dt.side;Dt.side=an,Dt.needsUpdate=!0,ui(St,Q,J,Xe,Dt,ut),Dt.side=en,Dt.needsUpdate=!0,ct=!0}}ct===!0&&(Je.updateMultisampleRenderTarget(pe),Je.updateRenderTargetMipmap(pe))}L.setRenderTarget(Ne,Ue,He),L.setClearColor(Z,he),_e!==void 0&&(J.viewport=_e),L.toneMapping=qe}function Nn(A,j,Q){const J=j.isScene===!0?j.overrideMaterial:null;for(let $=0,pe=A.length;$<pe;$++){const Re=A[$],Ne=Re.object,Ue=Re.geometry,He=Re.group;let qe=Re.material;qe.allowOverride===!0&&J!==null&&(qe=J),Ne.layers.test(Q.layers)&&ui(Ne,j,Q,Ue,qe,He)}}function ui(A,j,Q,J,$,pe){A.onBeforeRender(L,j,Q,J,$,pe),A.modelViewMatrix.multiplyMatrices(Q.matrixWorldInverse,A.matrixWorld),A.normalMatrix.getNormalMatrix(A.modelViewMatrix),$.onBeforeRender(L,j,Q,J,A,pe),$.transparent===!0&&$.side===Xn&&$.forceSinglePass===!1?($.side=an,$.needsUpdate=!0,L.renderBufferDirect(Q,j,J,$,A,pe),$.side=oi,$.needsUpdate=!0,L.renderBufferDirect(Q,j,J,$,A,pe),$.side=Xn):L.renderBufferDirect(Q,j,J,$,A,pe),A.onAfterRender(L,j,Q,J,$,pe)}function qn(A,j,Q){j.isScene!==!0&&(j=Ye);const J=Le.get(A),$=m.state.lights,pe=m.state.shadowsArray,Re=$.state.version,Ne=ne.getParameters(A,$.state,pe,j,Q),Ue=ne.getProgramCacheKey(Ne);let He=J.programs;J.environment=A.isMeshStandardMaterial?j.environment:null,J.fog=j.fog,J.envMap=(A.isMeshStandardMaterial?Et:Pt).get(A.envMap||J.environment),J.envMapRotation=J.environment!==null&&A.envMap===null?j.environmentRotation:A.envMapRotation,He===void 0&&(A.addEventListener("dispose",z),He=new Map,J.programs=He);let qe=He.get(Ue);if(qe!==void 0){if(J.currentProgram===qe&&J.lightsStateVersion===Re)return Lr(A,Ne),qe}else Ne.uniforms=ne.getUniforms(A),A.onBeforeCompile(Ne,L),qe=ne.acquireProgram(Ne,Ue),He.set(Ue,qe),J.uniforms=Ne.uniforms;const _e=J.uniforms;return(!A.isShaderMaterial&&!A.isRawShaderMaterial||A.clipping===!0)&&(_e.clippingPlanes=Me.uniform),Lr(A,Ne),J.needsLights=zs(A),J.lightsStateVersion=Re,J.needsLights&&(_e.ambientLightColor.value=$.state.ambient,_e.lightProbe.value=$.state.probe,_e.directionalLights.value=$.state.directional,_e.directionalLightShadows.value=$.state.directionalShadow,_e.spotLights.value=$.state.spot,_e.spotLightShadows.value=$.state.spotShadow,_e.rectAreaLights.value=$.state.rectArea,_e.ltc_1.value=$.state.rectAreaLTC1,_e.ltc_2.value=$.state.rectAreaLTC2,_e.pointLights.value=$.state.point,_e.pointLightShadows.value=$.state.pointShadow,_e.hemisphereLights.value=$.state.hemi,_e.directionalShadowMap.value=$.state.directionalShadowMap,_e.directionalShadowMatrix.value=$.state.directionalShadowMatrix,_e.spotShadowMap.value=$.state.spotShadowMap,_e.spotLightMatrix.value=$.state.spotLightMatrix,_e.spotLightMap.value=$.state.spotLightMap,_e.pointShadowMap.value=$.state.pointShadowMap,_e.pointShadowMatrix.value=$.state.pointShadowMatrix),J.currentProgram=qe,J.uniformsList=null,qe}function Dr(A){if(A.uniformsList===null){const j=A.currentProgram.getUniforms();A.uniformsList=Rs.seqWithValue(j.seq,A.uniforms)}return A.uniformsList}function Lr(A,j){const Q=Le.get(A);Q.outputColorSpace=j.outputColorSpace,Q.batching=j.batching,Q.batchingColor=j.batchingColor,Q.instancing=j.instancing,Q.instancingColor=j.instancingColor,Q.instancingMorph=j.instancingMorph,Q.skinning=j.skinning,Q.morphTargets=j.morphTargets,Q.morphNormals=j.morphNormals,Q.morphColors=j.morphColors,Q.morphTargetsCount=j.morphTargetsCount,Q.numClippingPlanes=j.numClippingPlanes,Q.numIntersection=j.numClipIntersection,Q.vertexAlphas=j.vertexAlphas,Q.vertexTangents=j.vertexTangents,Q.toneMapping=j.toneMapping}function Bs(A,j,Q,J,$){j.isScene!==!0&&(j=Ye),Je.resetTextureUnits();const pe=j.fog,Re=J.isMeshStandardMaterial?j.environment:null,Ne=q===null?L.outputColorSpace:q.isXRRenderTarget===!0?q.texture.colorSpace:rr,Ue=(J.isMeshStandardMaterial?Et:Pt).get(J.envMap||Re),He=J.vertexColors===!0&&!!Q.attributes.color&&Q.attributes.color.itemSize===4,qe=!!Q.attributes.tangent&&(!!J.normalMap||J.anisotropy>0),_e=!!Q.morphAttributes.position,ct=!!Q.morphAttributes.normal,vt=!!Q.morphAttributes.color;let It=ai;J.toneMapped&&(q===null||q.isXRRenderTarget===!0)&&(It=L.toneMapping);const Mt=Q.morphAttributes.position||Q.morphAttributes.normal||Q.morphAttributes.color,St=Mt!==void 0?Mt.length:0,Xe=Le.get(J),Dt=m.state.lights;if(ie===!0&&(Te===!0||A!==M)){const Yt=A===M&&J.id===P;Me.setState(J,A,Yt)}let ut=!1;J.version===Xe.__version?(Xe.needsLights&&Xe.lightsStateVersion!==Dt.state.version||Xe.outputColorSpace!==Ne||$.isBatchedMesh&&Xe.batching===!1||!$.isBatchedMesh&&Xe.batching===!0||$.isBatchedMesh&&Xe.batchingColor===!0&&$.colorTexture===null||$.isBatchedMesh&&Xe.batchingColor===!1&&$.colorTexture!==null||$.isInstancedMesh&&Xe.instancing===!1||!$.isInstancedMesh&&Xe.instancing===!0||$.isSkinnedMesh&&Xe.skinning===!1||!$.isSkinnedMesh&&Xe.skinning===!0||$.isInstancedMesh&&Xe.instancingColor===!0&&$.instanceColor===null||$.isInstancedMesh&&Xe.instancingColor===!1&&$.instanceColor!==null||$.isInstancedMesh&&Xe.instancingMorph===!0&&$.morphTexture===null||$.isInstancedMesh&&Xe.instancingMorph===!1&&$.morphTexture!==null||Xe.envMap!==Ue||J.fog===!0&&Xe.fog!==pe||Xe.numClippingPlanes!==void 0&&(Xe.numClippingPlanes!==Me.numPlanes||Xe.numIntersection!==Me.numIntersection)||Xe.vertexAlphas!==He||Xe.vertexTangents!==qe||Xe.morphTargets!==_e||Xe.morphNormals!==ct||Xe.morphColors!==vt||Xe.toneMapping!==It||Xe.morphTargetsCount!==St)&&(ut=!0):(ut=!0,Xe.__version=J.version);let en=Xe.currentProgram;ut===!0&&(en=qn(J,j,$));let On=!1,S=!1,yt=!1;const Lt=en.getUniforms(),qt=Xe.uniforms;if(Ge.useProgram(en.program)&&(On=!0,S=!0,yt=!0),J.id!==P&&(P=J.id,S=!0),On||M!==A){Ge.buffers.depth.getReversed()&&A.reversedDepth!==!0&&(A._reversedDepth=!0,A.updateProjectionMatrix()),Lt.setValue(k,"projectionMatrix",A.projectionMatrix),Lt.setValue(k,"viewMatrix",A.matrixWorldInverse);const Kt=Lt.map.cameraPosition;Kt!==void 0&&Kt.setValue(k,ue.setFromMatrixPosition(A.matrixWorld)),ft.logarithmicDepthBuffer&&Lt.setValue(k,"logDepthBufFC",2/(Math.log(A.far+1)/Math.LN2)),(J.isMeshPhongMaterial||J.isMeshToonMaterial||J.isMeshLambertMaterial||J.isMeshBasicMaterial||J.isMeshStandardMaterial||J.isShaderMaterial)&&Lt.setValue(k,"isOrthographic",A.isOrthographicCamera===!0),M!==A&&(M=A,S=!0,yt=!0)}if($.isSkinnedMesh){Lt.setOptional(k,$,"bindMatrix"),Lt.setOptional(k,$,"bindMatrixInverse");const Yt=$.skeleton;Yt&&(Yt.boneTexture===null&&Yt.computeBoneTexture(),Lt.setValue(k,"boneTexture",Yt.boneTexture,Je))}$.isBatchedMesh&&(Lt.setOptional(k,$,"batchingTexture"),Lt.setValue(k,"batchingTexture",$._matricesTexture,Je),Lt.setOptional(k,$,"batchingIdTexture"),Lt.setValue(k,"batchingIdTexture",$._indirectTexture,Je),Lt.setOptional(k,$,"batchingColorTexture"),$._colorsTexture!==null&&Lt.setValue(k,"batchingColorTexture",$._colorsTexture,Je));const Bt=Q.morphAttributes;if((Bt.position!==void 0||Bt.normal!==void 0||Bt.color!==void 0)&&xe.update($,Q,en),(S||Xe.receiveShadow!==$.receiveShadow)&&(Xe.receiveShadow=$.receiveShadow,Lt.setValue(k,"receiveShadow",$.receiveShadow)),J.isMeshGouraudMaterial&&J.envMap!==null&&(qt.envMap.value=Ue,qt.flipEnvMap.value=Ue.isCubeTexture&&Ue.isRenderTargetTexture===!1?-1:1),J.isMeshStandardMaterial&&J.envMap===null&&j.environment!==null&&(qt.envMapIntensity.value=j.environmentIntensity),S&&(Lt.setValue(k,"toneMappingExposure",L.toneMappingExposure),Xe.needsLights&&Ir(qt,yt),pe&&J.fog===!0&&de.refreshFogUniforms(qt,pe),de.refreshMaterialUniforms(qt,J,re,Se,m.state.transmissionRenderTarget[A.id]),Rs.upload(k,Dr(Xe),qt,Je)),J.isShaderMaterial&&J.uniformsNeedUpdate===!0&&(Rs.upload(k,Dr(Xe),qt,Je),J.uniformsNeedUpdate=!1),J.isSpriteMaterial&&Lt.setValue(k,"center",$.center),Lt.setValue(k,"modelViewMatrix",$.modelViewMatrix),Lt.setValue(k,"normalMatrix",$.normalMatrix),Lt.setValue(k,"modelMatrix",$.matrixWorld),J.isShaderMaterial||J.isRawShaderMaterial){const Yt=J.uniformsGroups;for(let Kt=0,lr=Yt.length;Kt<lr;Kt++){const kn=Yt[Kt];nt.update(kn,en),nt.bind(kn,en)}}return en}function Ir(A,j){A.ambientLightColor.needsUpdate=j,A.lightProbe.needsUpdate=j,A.directionalLights.needsUpdate=j,A.directionalLightShadows.needsUpdate=j,A.pointLights.needsUpdate=j,A.pointLightShadows.needsUpdate=j,A.spotLights.needsUpdate=j,A.spotLightShadows.needsUpdate=j,A.rectAreaLights.needsUpdate=j,A.hemisphereLights.needsUpdate=j}function zs(A){return A.isMeshLambertMaterial||A.isMeshToonMaterial||A.isMeshPhongMaterial||A.isMeshStandardMaterial||A.isShadowMaterial||A.isShaderMaterial&&A.lights===!0}this.getActiveCubeFace=function(){return D},this.getActiveMipmapLevel=function(){return H},this.getRenderTarget=function(){return q},this.setRenderTargetTextures=function(A,j,Q){const J=Le.get(A);J.__autoAllocateDepthBuffer=A.resolveDepthBuffer===!1,J.__autoAllocateDepthBuffer===!1&&(J.__useRenderToTexture=!1),Le.get(A.texture).__webglTexture=j,Le.get(A.depthTexture).__webglTexture=J.__autoAllocateDepthBuffer?void 0:Q,J.__hasExternalTextures=!0},this.setRenderTargetFramebuffer=function(A,j){const Q=Le.get(A);Q.__webglFramebuffer=j,Q.__useDefaultFramebuffer=j===void 0};const Hs=k.createFramebuffer();this.setRenderTarget=function(A,j=0,Q=0){q=A,D=j,H=Q;let J=!0,$=null,pe=!1,Re=!1;if(A){const Ue=Le.get(A);if(Ue.__useDefaultFramebuffer!==void 0)Ge.bindFramebuffer(k.FRAMEBUFFER,null),J=!1;else if(Ue.__webglFramebuffer===void 0)Je.setupRenderTarget(A);else if(Ue.__hasExternalTextures)Je.rebindTextures(A,Le.get(A.texture).__webglTexture,Le.get(A.depthTexture).__webglTexture);else if(A.depthBuffer){const _e=A.depthTexture;if(Ue.__boundDepthTexture!==_e){if(_e!==null&&Le.has(_e)&&(A.width!==_e.image.width||A.height!==_e.image.height))throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");Je.setupDepthRenderbuffer(A)}}const He=A.texture;(He.isData3DTexture||He.isDataArrayTexture||He.isCompressedArrayTexture)&&(Re=!0);const qe=Le.get(A).__webglFramebuffer;A.isWebGLCubeRenderTarget?(Array.isArray(qe[j])?$=qe[j][Q]:$=qe[j],pe=!0):A.samples>0&&Je.useMultisampledRTT(A)===!1?$=Le.get(A).__webglMultisampledFramebuffer:Array.isArray(qe)?$=qe[Q]:$=qe,O.copy(A.viewport),te.copy(A.scissor),ee=A.scissorTest}else O.copy(Ve).multiplyScalar(re).floor(),te.copy(tt).multiplyScalar(re).floor(),ee=xt;if(Q!==0&&($=Hs),Ge.bindFramebuffer(k.FRAMEBUFFER,$)&&J&&Ge.drawBuffers(A,$),Ge.viewport(O),Ge.scissor(te),Ge.setScissorTest(ee),pe){const Ue=Le.get(A.texture);k.framebufferTexture2D(k.FRAMEBUFFER,k.COLOR_ATTACHMENT0,k.TEXTURE_CUBE_MAP_POSITIVE_X+j,Ue.__webglTexture,Q)}else if(Re){const Ue=j;for(let He=0;He<A.textures.length;He++){const qe=Le.get(A.textures[He]);k.framebufferTextureLayer(k.FRAMEBUFFER,k.COLOR_ATTACHMENT0+He,qe.__webglTexture,Q,Ue)}}else if(A!==null&&Q!==0){const Ue=Le.get(A.texture);k.framebufferTexture2D(k.FRAMEBUFFER,k.COLOR_ATTACHMENT0,k.TEXTURE_2D,Ue.__webglTexture,Q)}P=-1},this.readRenderTargetPixels=function(A,j,Q,J,$,pe,Re,Ne=0){if(!(A&&A.isWebGLRenderTarget)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let Ue=Le.get(A).__webglFramebuffer;if(A.isWebGLCubeRenderTarget&&Re!==void 0&&(Ue=Ue[Re]),Ue){Ge.bindFramebuffer(k.FRAMEBUFFER,Ue);try{const He=A.textures[Ne],qe=He.format,_e=He.type;if(!ft.textureFormatReadable(qe)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(!ft.textureTypeReadable(_e)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}j>=0&&j<=A.width-J&&Q>=0&&Q<=A.height-$&&(A.textures.length>1&&k.readBuffer(k.COLOR_ATTACHMENT0+Ne),k.readPixels(j,Q,J,$,ke.convert(qe),ke.convert(_e),pe))}finally{const He=q!==null?Le.get(q).__webglFramebuffer:null;Ge.bindFramebuffer(k.FRAMEBUFFER,He)}}},this.readRenderTargetPixelsAsync=async function(A,j,Q,J,$,pe,Re,Ne=0){if(!(A&&A.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let Ue=Le.get(A).__webglFramebuffer;if(A.isWebGLCubeRenderTarget&&Re!==void 0&&(Ue=Ue[Re]),Ue)if(j>=0&&j<=A.width-J&&Q>=0&&Q<=A.height-$){Ge.bindFramebuffer(k.FRAMEBUFFER,Ue);const He=A.textures[Ne],qe=He.format,_e=He.type;if(!ft.textureFormatReadable(qe))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(!ft.textureTypeReadable(_e))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");const ct=k.createBuffer();k.bindBuffer(k.PIXEL_PACK_BUFFER,ct),k.bufferData(k.PIXEL_PACK_BUFFER,pe.byteLength,k.STREAM_READ),A.textures.length>1&&k.readBuffer(k.COLOR_ATTACHMENT0+Ne),k.readPixels(j,Q,J,$,ke.convert(qe),ke.convert(_e),0);const vt=q!==null?Le.get(q).__webglFramebuffer:null;Ge.bindFramebuffer(k.FRAMEBUFFER,vt);const It=k.fenceSync(k.SYNC_GPU_COMMANDS_COMPLETE,0);return k.flush(),await A_(k,It,4),k.bindBuffer(k.PIXEL_PACK_BUFFER,ct),k.getBufferSubData(k.PIXEL_PACK_BUFFER,0,pe),k.deleteBuffer(ct),k.deleteSync(It),pe}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")},this.copyFramebufferToTexture=function(A,j=null,Q=0){const J=Math.pow(2,-Q),$=Math.floor(A.image.width*J),pe=Math.floor(A.image.height*J),Re=j!==null?j.x:0,Ne=j!==null?j.y:0;Je.setTexture2D(A,0),k.copyTexSubImage2D(k.TEXTURE_2D,Q,0,0,Re,Ne,$,pe),Ge.unbindTexture()};const Vs=k.createFramebuffer(),Gs=k.createFramebuffer();this.copyTextureToTexture=function(A,j,Q=null,J=null,$=0,pe=null){pe===null&&($!==0?(Qi("WebGLRenderer: copyTextureToTexture function signature has changed to support src and dst mipmap levels."),pe=$,$=0):pe=0);let Re,Ne,Ue,He,qe,_e,ct,vt,It;const Mt=A.isCompressedTexture?A.mipmaps[pe]:A.image;if(Q!==null)Re=Q.max.x-Q.min.x,Ne=Q.max.y-Q.min.y,Ue=Q.isBox3?Q.max.z-Q.min.z:1,He=Q.min.x,qe=Q.min.y,_e=Q.isBox3?Q.min.z:0;else{const Bt=Math.pow(2,-$);Re=Math.floor(Mt.width*Bt),Ne=Math.floor(Mt.height*Bt),A.isDataArrayTexture?Ue=Mt.depth:A.isData3DTexture?Ue=Math.floor(Mt.depth*Bt):Ue=1,He=0,qe=0,_e=0}J!==null?(ct=J.x,vt=J.y,It=J.z):(ct=0,vt=0,It=0);const St=ke.convert(j.format),Xe=ke.convert(j.type);let Dt;j.isData3DTexture?(Je.setTexture3D(j,0),Dt=k.TEXTURE_3D):j.isDataArrayTexture||j.isCompressedArrayTexture?(Je.setTexture2DArray(j,0),Dt=k.TEXTURE_2D_ARRAY):(Je.setTexture2D(j,0),Dt=k.TEXTURE_2D),k.pixelStorei(k.UNPACK_FLIP_Y_WEBGL,j.flipY),k.pixelStorei(k.UNPACK_PREMULTIPLY_ALPHA_WEBGL,j.premultiplyAlpha),k.pixelStorei(k.UNPACK_ALIGNMENT,j.unpackAlignment);const ut=k.getParameter(k.UNPACK_ROW_LENGTH),en=k.getParameter(k.UNPACK_IMAGE_HEIGHT),On=k.getParameter(k.UNPACK_SKIP_PIXELS),S=k.getParameter(k.UNPACK_SKIP_ROWS),yt=k.getParameter(k.UNPACK_SKIP_IMAGES);k.pixelStorei(k.UNPACK_ROW_LENGTH,Mt.width),k.pixelStorei(k.UNPACK_IMAGE_HEIGHT,Mt.height),k.pixelStorei(k.UNPACK_SKIP_PIXELS,He),k.pixelStorei(k.UNPACK_SKIP_ROWS,qe),k.pixelStorei(k.UNPACK_SKIP_IMAGES,_e);const Lt=A.isDataArrayTexture||A.isData3DTexture,qt=j.isDataArrayTexture||j.isData3DTexture;if(A.isDepthTexture){const Bt=Le.get(A),Yt=Le.get(j),Kt=Le.get(Bt.__renderTarget),lr=Le.get(Yt.__renderTarget);Ge.bindFramebuffer(k.READ_FRAMEBUFFER,Kt.__webglFramebuffer),Ge.bindFramebuffer(k.DRAW_FRAMEBUFFER,lr.__webglFramebuffer);for(let kn=0;kn<Ue;kn++)Lt&&(k.framebufferTextureLayer(k.READ_FRAMEBUFFER,k.COLOR_ATTACHMENT0,Le.get(A).__webglTexture,$,_e+kn),k.framebufferTextureLayer(k.DRAW_FRAMEBUFFER,k.COLOR_ATTACHMENT0,Le.get(j).__webglTexture,pe,It+kn)),k.blitFramebuffer(He,qe,Re,Ne,ct,vt,Re,Ne,k.DEPTH_BUFFER_BIT,k.NEAREST);Ge.bindFramebuffer(k.READ_FRAMEBUFFER,null),Ge.bindFramebuffer(k.DRAW_FRAMEBUFFER,null)}else if($!==0||A.isRenderTargetTexture||Le.has(A)){const Bt=Le.get(A),Yt=Le.get(j);Ge.bindFramebuffer(k.READ_FRAMEBUFFER,Vs),Ge.bindFramebuffer(k.DRAW_FRAMEBUFFER,Gs);for(let Kt=0;Kt<Ue;Kt++)Lt?k.framebufferTextureLayer(k.READ_FRAMEBUFFER,k.COLOR_ATTACHMENT0,Bt.__webglTexture,$,_e+Kt):k.framebufferTexture2D(k.READ_FRAMEBUFFER,k.COLOR_ATTACHMENT0,k.TEXTURE_2D,Bt.__webglTexture,$),qt?k.framebufferTextureLayer(k.DRAW_FRAMEBUFFER,k.COLOR_ATTACHMENT0,Yt.__webglTexture,pe,It+Kt):k.framebufferTexture2D(k.DRAW_FRAMEBUFFER,k.COLOR_ATTACHMENT0,k.TEXTURE_2D,Yt.__webglTexture,pe),$!==0?k.blitFramebuffer(He,qe,Re,Ne,ct,vt,Re,Ne,k.COLOR_BUFFER_BIT,k.NEAREST):qt?k.copyTexSubImage3D(Dt,pe,ct,vt,It+Kt,He,qe,Re,Ne):k.copyTexSubImage2D(Dt,pe,ct,vt,He,qe,Re,Ne);Ge.bindFramebuffer(k.READ_FRAMEBUFFER,null),Ge.bindFramebuffer(k.DRAW_FRAMEBUFFER,null)}else qt?A.isDataTexture||A.isData3DTexture?k.texSubImage3D(Dt,pe,ct,vt,It,Re,Ne,Ue,St,Xe,Mt.data):j.isCompressedArrayTexture?k.compressedTexSubImage3D(Dt,pe,ct,vt,It,Re,Ne,Ue,St,Mt.data):k.texSubImage3D(Dt,pe,ct,vt,It,Re,Ne,Ue,St,Xe,Mt):A.isDataTexture?k.texSubImage2D(k.TEXTURE_2D,pe,ct,vt,Re,Ne,St,Xe,Mt.data):A.isCompressedTexture?k.compressedTexSubImage2D(k.TEXTURE_2D,pe,ct,vt,Mt.width,Mt.height,St,Mt.data):k.texSubImage2D(k.TEXTURE_2D,pe,ct,vt,Re,Ne,St,Xe,Mt);k.pixelStorei(k.UNPACK_ROW_LENGTH,ut),k.pixelStorei(k.UNPACK_IMAGE_HEIGHT,en),k.pixelStorei(k.UNPACK_SKIP_PIXELS,On),k.pixelStorei(k.UNPACK_SKIP_ROWS,S),k.pixelStorei(k.UNPACK_SKIP_IMAGES,yt),pe===0&&j.generateMipmaps&&k.generateMipmap(Dt),Ge.unbindTexture()},this.copyTextureToTexture3D=function(A,j,Q=null,J=null,$=0){return Qi('WebGLRenderer: copyTextureToTexture3D function has been deprecated. Use "copyTextureToTexture" instead.'),this.copyTextureToTexture(A,j,Q,J,$)},this.initRenderTarget=function(A){Le.get(A).__webglFramebuffer===void 0&&Je.setupRenderTarget(A)},this.initTexture=function(A){A.isCubeTexture?Je.setTextureCube(A,0):A.isData3DTexture?Je.setTexture3D(A,0):A.isDataArrayTexture||A.isCompressedArrayTexture?Je.setTexture2DArray(A,0):Je.setTexture2D(A,0),Ge.unbindTexture()},this.resetState=function(){D=0,H=0,q=null,Ge.reset(),we.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return Dn}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(e){this._outputColorSpace=e;const t=this.getContext();t.drawingBufferColorSpace=gt._getDrawingBufferColorSpace(e),t.unpackColorSpace=gt._getUnpackColorSpace()}}const Vl={type:"change"},jo={type:"start"},Tu={type:"end"},Es=new Ns,Gl=new ti,Ky=Math.cos(70*b_.DEG2RAD),Gt=new X,sn=2*Math.PI,wt={NONE:-1,ROTATE:0,DOLLY:1,PAN:2,TOUCH_ROTATE:3,TOUCH_PAN:4,TOUCH_DOLLY_PAN:5,TOUCH_DOLLY_ROTATE:6},Oa=1e-6;class Zy extends dg{constructor(e,t=null){super(e,t),this.state=wt.NONE,this.target=new X,this.cursor=new X,this.minDistance=0,this.maxDistance=1/0,this.minZoom=0,this.maxZoom=1/0,this.minTargetRadius=0,this.maxTargetRadius=1/0,this.minPolarAngle=0,this.maxPolarAngle=Math.PI,this.minAzimuthAngle=-1/0,this.maxAzimuthAngle=1/0,this.enableDamping=!1,this.dampingFactor=.05,this.enableZoom=!0,this.zoomSpeed=1,this.enableRotate=!0,this.rotateSpeed=1,this.keyRotateSpeed=1,this.enablePan=!0,this.panSpeed=1,this.screenSpacePanning=!0,this.keyPanSpeed=7,this.zoomToCursor=!1,this.autoRotate=!1,this.autoRotateSpeed=2,this.keys={LEFT:"ArrowLeft",UP:"ArrowUp",RIGHT:"ArrowRight",BOTTOM:"ArrowDown"},this.mouseButtons={LEFT:Zi.ROTATE,MIDDLE:Zi.DOLLY,RIGHT:Zi.PAN},this.touches={ONE:Yi.ROTATE,TWO:Yi.DOLLY_PAN},this.target0=this.target.clone(),this.position0=this.object.position.clone(),this.zoom0=this.object.zoom,this._domElementKeyEvents=null,this._lastPosition=new X,this._lastQuaternion=new Ci,this._lastTargetPosition=new X,this._quat=new Ci().setFromUnitVectors(e.up,new X(0,1,0)),this._quatInverse=this._quat.clone().invert(),this._spherical=new ml,this._sphericalDelta=new ml,this._scale=1,this._panOffset=new X,this._rotateStart=new et,this._rotateEnd=new et,this._rotateDelta=new et,this._panStart=new et,this._panEnd=new et,this._panDelta=new et,this._dollyStart=new et,this._dollyEnd=new et,this._dollyDelta=new et,this._dollyDirection=new X,this._mouse=new et,this._performCursorZoom=!1,this._pointers=[],this._pointerPositions={},this._controlActive=!1,this._onPointerMove=Qy.bind(this),this._onPointerDown=Jy.bind(this),this._onPointerUp=eE.bind(this),this._onContextMenu=oE.bind(this),this._onMouseWheel=iE.bind(this),this._onKeyDown=rE.bind(this),this._onTouchStart=sE.bind(this),this._onTouchMove=aE.bind(this),this._onMouseDown=tE.bind(this),this._onMouseMove=nE.bind(this),this._interceptControlDown=cE.bind(this),this._interceptControlUp=lE.bind(this),this.domElement!==null&&this.connect(this.domElement),this.update()}connect(e){super.connect(e),this.domElement.addEventListener("pointerdown",this._onPointerDown),this.domElement.addEventListener("pointercancel",this._onPointerUp),this.domElement.addEventListener("contextmenu",this._onContextMenu),this.domElement.addEventListener("wheel",this._onMouseWheel,{passive:!1}),this.domElement.getRootNode().addEventListener("keydown",this._interceptControlDown,{passive:!0,capture:!0}),this.domElement.style.touchAction="none"}disconnect(){this.domElement.removeEventListener("pointerdown",this._onPointerDown),this.domElement.removeEventListener("pointermove",this._onPointerMove),this.domElement.removeEventListener("pointerup",this._onPointerUp),this.domElement.removeEventListener("pointercancel",this._onPointerUp),this.domElement.removeEventListener("wheel",this._onMouseWheel),this.domElement.removeEventListener("contextmenu",this._onContextMenu),this.stopListenToKeyEvents(),this.domElement.getRootNode().removeEventListener("keydown",this._interceptControlDown,{capture:!0}),this.domElement.style.touchAction="auto"}dispose(){this.disconnect()}getPolarAngle(){return this._spherical.phi}getAzimuthalAngle(){return this._spherical.theta}getDistance(){return this.object.position.distanceTo(this.target)}listenToKeyEvents(e){e.addEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=e}stopListenToKeyEvents(){this._domElementKeyEvents!==null&&(this._domElementKeyEvents.removeEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=null)}saveState(){this.target0.copy(this.target),this.position0.copy(this.object.position),this.zoom0=this.object.zoom}reset(){this.target.copy(this.target0),this.object.position.copy(this.position0),this.object.zoom=this.zoom0,this.object.updateProjectionMatrix(),this.dispatchEvent(Vl),this.update(),this.state=wt.NONE}update(e=null){const t=this.object.position;Gt.copy(t).sub(this.target),Gt.applyQuaternion(this._quat),this._spherical.setFromVector3(Gt),this.autoRotate&&this.state===wt.NONE&&this._rotateLeft(this._getAutoRotationAngle(e)),this.enableDamping?(this._spherical.theta+=this._sphericalDelta.theta*this.dampingFactor,this._spherical.phi+=this._sphericalDelta.phi*this.dampingFactor):(this._spherical.theta+=this._sphericalDelta.theta,this._spherical.phi+=this._sphericalDelta.phi);let n=this.minAzimuthAngle,a=this.maxAzimuthAngle;isFinite(n)&&isFinite(a)&&(n<-Math.PI?n+=sn:n>Math.PI&&(n-=sn),a<-Math.PI?a+=sn:a>Math.PI&&(a-=sn),n<=a?this._spherical.theta=Math.max(n,Math.min(a,this._spherical.theta)):this._spherical.theta=this._spherical.theta>(n+a)/2?Math.max(n,this._spherical.theta):Math.min(a,this._spherical.theta)),this._spherical.phi=Math.max(this.minPolarAngle,Math.min(this.maxPolarAngle,this._spherical.phi)),this._spherical.makeSafe(),this.enableDamping===!0?this.target.addScaledVector(this._panOffset,this.dampingFactor):this.target.add(this._panOffset),this.target.sub(this.cursor),this.target.clampLength(this.minTargetRadius,this.maxTargetRadius),this.target.add(this.cursor);let o=!1;if(this.zoomToCursor&&this._performCursorZoom||this.object.isOrthographicCamera)this._spherical.radius=this._clampDistance(this._spherical.radius);else{const l=this._spherical.radius;this._spherical.radius=this._clampDistance(this._spherical.radius*this._scale),o=l!=this._spherical.radius}if(Gt.setFromSpherical(this._spherical),Gt.applyQuaternion(this._quatInverse),t.copy(this.target).add(Gt),this.object.lookAt(this.target),this.enableDamping===!0?(this._sphericalDelta.theta*=1-this.dampingFactor,this._sphericalDelta.phi*=1-this.dampingFactor,this._panOffset.multiplyScalar(1-this.dampingFactor)):(this._sphericalDelta.set(0,0,0),this._panOffset.set(0,0,0)),this.zoomToCursor&&this._performCursorZoom){let l=null;if(this.object.isPerspectiveCamera){const u=Gt.length();l=this._clampDistance(u*this._scale);const p=u-l;this.object.position.addScaledVector(this._dollyDirection,p),this.object.updateMatrixWorld(),o=!!p}else if(this.object.isOrthographicCamera){const u=new X(this._mouse.x,this._mouse.y,0);u.unproject(this.object);const p=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),this.object.updateProjectionMatrix(),o=p!==this.object.zoom;const f=new X(this._mouse.x,this._mouse.y,0);f.unproject(this.object),this.object.position.sub(f).add(u),this.object.updateMatrixWorld(),l=Gt.length()}else console.warn("WARNING: OrbitControls.js encountered an unknown camera type - zoom to cursor disabled."),this.zoomToCursor=!1;l!==null&&(this.screenSpacePanning?this.target.set(0,0,-1).transformDirection(this.object.matrix).multiplyScalar(l).add(this.object.position):(Es.origin.copy(this.object.position),Es.direction.set(0,0,-1).transformDirection(this.object.matrix),Math.abs(this.object.up.dot(Es.direction))<Ky?this.object.lookAt(this.target):(Gl.setFromNormalAndCoplanarPoint(this.object.up,this.target),Es.intersectPlane(Gl,this.target))))}else if(this.object.isOrthographicCamera){const l=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),l!==this.object.zoom&&(this.object.updateProjectionMatrix(),o=!0)}return this._scale=1,this._performCursorZoom=!1,o||this._lastPosition.distanceToSquared(this.object.position)>Oa||8*(1-this._lastQuaternion.dot(this.object.quaternion))>Oa||this._lastTargetPosition.distanceToSquared(this.target)>Oa?(this.dispatchEvent(Vl),this._lastPosition.copy(this.object.position),this._lastQuaternion.copy(this.object.quaternion),this._lastTargetPosition.copy(this.target),!0):!1}_getAutoRotationAngle(e){return e!==null?sn/60*this.autoRotateSpeed*e:sn/60/60*this.autoRotateSpeed}_getZoomScale(e){const t=Math.abs(e*.01);return Math.pow(.95,this.zoomSpeed*t)}_rotateLeft(e){this._sphericalDelta.theta-=e}_rotateUp(e){this._sphericalDelta.phi-=e}_panLeft(e,t){Gt.setFromMatrixColumn(t,0),Gt.multiplyScalar(-e),this._panOffset.add(Gt)}_panUp(e,t){this.screenSpacePanning===!0?Gt.setFromMatrixColumn(t,1):(Gt.setFromMatrixColumn(t,0),Gt.crossVectors(this.object.up,Gt)),Gt.multiplyScalar(e),this._panOffset.add(Gt)}_pan(e,t){const n=this.domElement;if(this.object.isPerspectiveCamera){const a=this.object.position;Gt.copy(a).sub(this.target);let o=Gt.length();o*=Math.tan(this.object.fov/2*Math.PI/180),this._panLeft(2*e*o/n.clientHeight,this.object.matrix),this._panUp(2*t*o/n.clientHeight,this.object.matrix)}else this.object.isOrthographicCamera?(this._panLeft(e*(this.object.right-this.object.left)/this.object.zoom/n.clientWidth,this.object.matrix),this._panUp(t*(this.object.top-this.object.bottom)/this.object.zoom/n.clientHeight,this.object.matrix)):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - pan disabled."),this.enablePan=!1)}_dollyOut(e){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale/=e:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_dollyIn(e){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale*=e:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_updateZoomParameters(e,t){if(!this.zoomToCursor)return;this._performCursorZoom=!0;const n=this.domElement.getBoundingClientRect(),a=e-n.left,o=t-n.top,l=n.width,u=n.height;this._mouse.x=a/l*2-1,this._mouse.y=-(o/u)*2+1,this._dollyDirection.set(this._mouse.x,this._mouse.y,1).unproject(this.object).sub(this.object.position).normalize()}_clampDistance(e){return Math.max(this.minDistance,Math.min(this.maxDistance,e))}_handleMouseDownRotate(e){this._rotateStart.set(e.clientX,e.clientY)}_handleMouseDownDolly(e){this._updateZoomParameters(e.clientX,e.clientX),this._dollyStart.set(e.clientX,e.clientY)}_handleMouseDownPan(e){this._panStart.set(e.clientX,e.clientY)}_handleMouseMoveRotate(e){this._rotateEnd.set(e.clientX,e.clientY),this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);const t=this.domElement;this._rotateLeft(sn*this._rotateDelta.x/t.clientHeight),this._rotateUp(sn*this._rotateDelta.y/t.clientHeight),this._rotateStart.copy(this._rotateEnd),this.update()}_handleMouseMoveDolly(e){this._dollyEnd.set(e.clientX,e.clientY),this._dollyDelta.subVectors(this._dollyEnd,this._dollyStart),this._dollyDelta.y>0?this._dollyOut(this._getZoomScale(this._dollyDelta.y)):this._dollyDelta.y<0&&this._dollyIn(this._getZoomScale(this._dollyDelta.y)),this._dollyStart.copy(this._dollyEnd),this.update()}_handleMouseMovePan(e){this._panEnd.set(e.clientX,e.clientY),this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd),this.update()}_handleMouseWheel(e){this._updateZoomParameters(e.clientX,e.clientY),e.deltaY<0?this._dollyIn(this._getZoomScale(e.deltaY)):e.deltaY>0&&this._dollyOut(this._getZoomScale(e.deltaY)),this.update()}_handleKeyDown(e){let t=!1;switch(e.code){case this.keys.UP:e.ctrlKey||e.metaKey||e.shiftKey?this.enableRotate&&this._rotateUp(sn*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(0,this.keyPanSpeed),t=!0;break;case this.keys.BOTTOM:e.ctrlKey||e.metaKey||e.shiftKey?this.enableRotate&&this._rotateUp(-sn*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(0,-this.keyPanSpeed),t=!0;break;case this.keys.LEFT:e.ctrlKey||e.metaKey||e.shiftKey?this.enableRotate&&this._rotateLeft(sn*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(this.keyPanSpeed,0),t=!0;break;case this.keys.RIGHT:e.ctrlKey||e.metaKey||e.shiftKey?this.enableRotate&&this._rotateLeft(-sn*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(-this.keyPanSpeed,0),t=!0;break}t&&(e.preventDefault(),this.update())}_handleTouchStartRotate(e){if(this._pointers.length===1)this._rotateStart.set(e.pageX,e.pageY);else{const t=this._getSecondPointerPosition(e),n=.5*(e.pageX+t.x),a=.5*(e.pageY+t.y);this._rotateStart.set(n,a)}}_handleTouchStartPan(e){if(this._pointers.length===1)this._panStart.set(e.pageX,e.pageY);else{const t=this._getSecondPointerPosition(e),n=.5*(e.pageX+t.x),a=.5*(e.pageY+t.y);this._panStart.set(n,a)}}_handleTouchStartDolly(e){const t=this._getSecondPointerPosition(e),n=e.pageX-t.x,a=e.pageY-t.y,o=Math.sqrt(n*n+a*a);this._dollyStart.set(0,o)}_handleTouchStartDollyPan(e){this.enableZoom&&this._handleTouchStartDolly(e),this.enablePan&&this._handleTouchStartPan(e)}_handleTouchStartDollyRotate(e){this.enableZoom&&this._handleTouchStartDolly(e),this.enableRotate&&this._handleTouchStartRotate(e)}_handleTouchMoveRotate(e){if(this._pointers.length==1)this._rotateEnd.set(e.pageX,e.pageY);else{const n=this._getSecondPointerPosition(e),a=.5*(e.pageX+n.x),o=.5*(e.pageY+n.y);this._rotateEnd.set(a,o)}this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);const t=this.domElement;this._rotateLeft(sn*this._rotateDelta.x/t.clientHeight),this._rotateUp(sn*this._rotateDelta.y/t.clientHeight),this._rotateStart.copy(this._rotateEnd)}_handleTouchMovePan(e){if(this._pointers.length===1)this._panEnd.set(e.pageX,e.pageY);else{const t=this._getSecondPointerPosition(e),n=.5*(e.pageX+t.x),a=.5*(e.pageY+t.y);this._panEnd.set(n,a)}this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd)}_handleTouchMoveDolly(e){const t=this._getSecondPointerPosition(e),n=e.pageX-t.x,a=e.pageY-t.y,o=Math.sqrt(n*n+a*a);this._dollyEnd.set(0,o),this._dollyDelta.set(0,Math.pow(this._dollyEnd.y/this._dollyStart.y,this.zoomSpeed)),this._dollyOut(this._dollyDelta.y),this._dollyStart.copy(this._dollyEnd);const l=(e.pageX+t.x)*.5,u=(e.pageY+t.y)*.5;this._updateZoomParameters(l,u)}_handleTouchMoveDollyPan(e){this.enableZoom&&this._handleTouchMoveDolly(e),this.enablePan&&this._handleTouchMovePan(e)}_handleTouchMoveDollyRotate(e){this.enableZoom&&this._handleTouchMoveDolly(e),this.enableRotate&&this._handleTouchMoveRotate(e)}_addPointer(e){this._pointers.push(e.pointerId)}_removePointer(e){delete this._pointerPositions[e.pointerId];for(let t=0;t<this._pointers.length;t++)if(this._pointers[t]==e.pointerId){this._pointers.splice(t,1);return}}_isTrackingPointer(e){for(let t=0;t<this._pointers.length;t++)if(this._pointers[t]==e.pointerId)return!0;return!1}_trackPointer(e){let t=this._pointerPositions[e.pointerId];t===void 0&&(t=new et,this._pointerPositions[e.pointerId]=t),t.set(e.pageX,e.pageY)}_getSecondPointerPosition(e){const t=e.pointerId===this._pointers[0]?this._pointers[1]:this._pointers[0];return this._pointerPositions[t]}_customWheelEvent(e){const t=e.deltaMode,n={clientX:e.clientX,clientY:e.clientY,deltaY:e.deltaY};switch(t){case 1:n.deltaY*=16;break;case 2:n.deltaY*=100;break}return e.ctrlKey&&!this._controlActive&&(n.deltaY*=10),n}}function Jy(r){this.enabled!==!1&&(this._pointers.length===0&&(this.domElement.setPointerCapture(r.pointerId),this.domElement.addEventListener("pointermove",this._onPointerMove),this.domElement.addEventListener("pointerup",this._onPointerUp)),!this._isTrackingPointer(r)&&(this._addPointer(r),r.pointerType==="touch"?this._onTouchStart(r):this._onMouseDown(r)))}function Qy(r){this.enabled!==!1&&(r.pointerType==="touch"?this._onTouchMove(r):this._onMouseMove(r))}function eE(r){switch(this._removePointer(r),this._pointers.length){case 0:this.domElement.releasePointerCapture(r.pointerId),this.domElement.removeEventListener("pointermove",this._onPointerMove),this.domElement.removeEventListener("pointerup",this._onPointerUp),this.dispatchEvent(Tu),this.state=wt.NONE;break;case 1:const e=this._pointers[0],t=this._pointerPositions[e];this._onTouchStart({pointerId:e,pageX:t.x,pageY:t.y});break}}function tE(r){let e;switch(r.button){case 0:e=this.mouseButtons.LEFT;break;case 1:e=this.mouseButtons.MIDDLE;break;case 2:e=this.mouseButtons.RIGHT;break;default:e=-1}switch(e){case Zi.DOLLY:if(this.enableZoom===!1)return;this._handleMouseDownDolly(r),this.state=wt.DOLLY;break;case Zi.ROTATE:if(r.ctrlKey||r.metaKey||r.shiftKey){if(this.enablePan===!1)return;this._handleMouseDownPan(r),this.state=wt.PAN}else{if(this.enableRotate===!1)return;this._handleMouseDownRotate(r),this.state=wt.ROTATE}break;case Zi.PAN:if(r.ctrlKey||r.metaKey||r.shiftKey){if(this.enableRotate===!1)return;this._handleMouseDownRotate(r),this.state=wt.ROTATE}else{if(this.enablePan===!1)return;this._handleMouseDownPan(r),this.state=wt.PAN}break;default:this.state=wt.NONE}this.state!==wt.NONE&&this.dispatchEvent(jo)}function nE(r){switch(this.state){case wt.ROTATE:if(this.enableRotate===!1)return;this._handleMouseMoveRotate(r);break;case wt.DOLLY:if(this.enableZoom===!1)return;this._handleMouseMoveDolly(r);break;case wt.PAN:if(this.enablePan===!1)return;this._handleMouseMovePan(r);break}}function iE(r){this.enabled===!1||this.enableZoom===!1||this.state!==wt.NONE||(r.preventDefault(),this.dispatchEvent(jo),this._handleMouseWheel(this._customWheelEvent(r)),this.dispatchEvent(Tu))}function rE(r){this.enabled!==!1&&this._handleKeyDown(r)}function sE(r){switch(this._trackPointer(r),this._pointers.length){case 1:switch(this.touches.ONE){case Yi.ROTATE:if(this.enableRotate===!1)return;this._handleTouchStartRotate(r),this.state=wt.TOUCH_ROTATE;break;case Yi.PAN:if(this.enablePan===!1)return;this._handleTouchStartPan(r),this.state=wt.TOUCH_PAN;break;default:this.state=wt.NONE}break;case 2:switch(this.touches.TWO){case Yi.DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchStartDollyPan(r),this.state=wt.TOUCH_DOLLY_PAN;break;case Yi.DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchStartDollyRotate(r),this.state=wt.TOUCH_DOLLY_ROTATE;break;default:this.state=wt.NONE}break;default:this.state=wt.NONE}this.state!==wt.NONE&&this.dispatchEvent(jo)}function aE(r){switch(this._trackPointer(r),this.state){case wt.TOUCH_ROTATE:if(this.enableRotate===!1)return;this._handleTouchMoveRotate(r),this.update();break;case wt.TOUCH_PAN:if(this.enablePan===!1)return;this._handleTouchMovePan(r),this.update();break;case wt.TOUCH_DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchMoveDollyPan(r),this.update();break;case wt.TOUCH_DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchMoveDollyRotate(r),this.update();break;default:this.state=wt.NONE}}function oE(r){this.enabled!==!1&&r.preventDefault()}function cE(r){r.key==="Control"&&(this._controlActive=!0,this.domElement.getRootNode().addEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}function lE(r){r.key==="Control"&&(this._controlActive=!1,this.domElement.getRootNode().removeEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}function bu(r,e){return Number.isInteger(e)&&e>=0?Math.max(r,e):r}function uE(r,e,t){return!!(r&&e&&t&&e.seq===t.seq)}function hE(r,e){const t=bu(r?.seq||0,e)+1;return{...r,seq:t}}function dE(r,e){return r&&e>.005&&(r.visualStarted=!0),!!r?.visualStarted}function fE(r,e){const t=3*e;if(!Number.isInteger(e)||e<=0||!r||t+2>=r.length)return null;const n=[Number(r[t]),Number(r[t+1]),Number(r[t+2])];return n.every(Number.isFinite)?n:null}const ii=(r,e)=>r&&r.length===e&&Array.from(r).every(Number.isFinite),wu=r=>Math.atan2(Math.sin(r),Math.cos(r)),pE=(r,e)=>wu(e-r);function mE(r){if(!ii(r,4))return null;const e=Math.hypot(...r);if(!(e>1e-12))return null;const[t,n,a,o]=Array.from(r,l=>l/e);return Math.atan2(2*(t*o+n*a),1-2*(a*a+o*o))}function _E(r,e,t){if(!ii(r,4)||!ii(e,4))return null;let n=r.reduce((u,p,f)=>u+p*e[f],0);const a=n<0?-1:1;n*=a;const o=r.map((u,p)=>u+(a*e[p]-u)*t),l=Math.hypot(...o);return!(l>1e-12)||!Number.isFinite(n)?null:o.map(u=>u/l)}function gE(r,e,t,n,a){const o=Number(a?.quaternion_qpos_adr);if(a?.schema!==1||a.available!==!0||!Number.isInteger(o)||o<0||!r||r.length<o+4||!e||e.length<o+4||!t||t.length<o+4)return!1;const l=_E(Array.from(e.slice(o,o+4)),Array.from(t.slice(o,o+4)),n);if(!l)return!1;for(let u=0;u<4;u++)r[o+u]=l[u];return!0}class vE{constructor(e,t){this.configure(e,t)}configure(e={},t={}){this.rootPose={available:t.schema===1&&t.available===!0,position_qpos_adr:Number(t.position_qpos_adr),quaternion_qpos_adr:Number(t.quaternion_qpos_adr)},this.config={enabled:e.schema===1&&e.enabled===!0&&this.rootPose.available,follow_yaw:e.follow_yaw===!0,lookat_offset:ii(e.lookat_offset,3)?[...e.lookat_offset]:[0,0,0],smoothing_tau:Number.isFinite(e.smoothing_tau)&&e.smoothing_tau>=0?e.smoothing_tau:0},(!Number.isInteger(this.rootPose.position_qpos_adr)||this.rootPose.position_qpos_adr<0||!Number.isInteger(this.rootPose.quaternion_qpos_adr)||this.rootPose.quaternion_qpos_adr<0)&&(this.config.enabled=!1),this.camera=[0,0,0],this.target=[0,0,0],this.lastYaw=0,this.smoothedTarget=null}reset(){this.smoothedTarget=null}update(e,t,n,a=0){const o=[...t],l=[...n],u=()=>(this.camera=o,this.target=l,{camera:o,target:l,yaw_delta:0,applied:!1});if(!this.config.enabled||!ii(e,e?.length)||!ii(o,3)||!ii(l,3))return u();const p=Array.from(e.slice(this.rootPose.position_qpos_adr,this.rootPose.position_qpos_adr+3)),f=Array.from(e.slice(this.rootPose.quaternion_qpos_adr,this.rootPose.quaternion_qpos_adr+4)),_=mE(f);if(!ii(p,3)||_===null)return u();const v=[...this.config.lookat_offset];if(this.config.follow_yaw){const m=Math.cos(_),N=Math.sin(_);[v[0],v[1]]=[m*v[0]-N*v[1],N*v[0]+m*v[1]]}const x=p.map((m,N)=>m+v[N]),E=this.config.smoothing_tau,R=E>0&&a>0?1-Math.exp(-Math.min(a,.1)/E):1;this.smoothedTarget===null?this.smoothedTarget=x:this.smoothedTarget=this.smoothedTarget.map((m,N)=>m+R*(x[N]-m));const C=this.smoothedTarget.map((m,N)=>m-l[N]);for(let m=0;m<3;m++)o[m]+=C[m],l[m]=this.smoothedTarget[m];let y=0;if(this.config.follow_yaw){y=pE(this.lastYaw,_)*R;const m=o[0]-l[0],N=o[1]-l[1],I=Math.cos(y),L=Math.sin(y);o[0]=l[0]+I*m-L*N,o[1]=l[1]+L*m+I*N,this.lastYaw=wu(this.lastYaw+y)}else this.lastYaw=_;return this.camera=o,this.target=l,{camera:o,target:l,yaw_delta:y,applied:!0}}}const ka=r=>Array.isArray(r)&&r.length===3&&r.every(e=>Number.isFinite(Number(e)));function xE(r){const e=ka(r?.display_target)?r.display_target:ka(r?.render_target)?r.render_target:r?.target,t=ka(e)?e.map(Number):null;return{visible:t!==null,active:!!r?.enabled,target:t}}const xr=80,Wl=15180075,yE=15527146,EE=16726832,qi={dark:{clear:724239,fog:{color:724239,near:8,far:24},exposure:1.08,hemisphere:{sky:14542055,ground:1514013,intensity:1.15},key_light:{color:16773862,intensity:2.5},rim_light:{color:16742938,intensity:.85},ground:2106666,grid:{center:9082527,line:5857897,opacity:.62},robot:{odd:7502722,even:5265760,pelvis:12016683},selection:16742938},light:{clear:15133163,fog:{color:15133163,near:11,far:30},exposure:.96,hemisphere:{sky:16777215,ground:11449528,intensity:1.7},key_light:{color:16777215,intensity:2.15},rim_light:{color:13620439,intensity:1.1},ground:13093838,grid:{center:7568256,line:10988977,opacity:.72},robot:{odd:6450033,even:3423040,pelvis:11027992},selection:14243584}},Po=r=>{console.error(r),window.dispatchEvent(new CustomEvent("mujoco-error",{detail:String(r.message||r)}))},Au=r=>[...new Uint8Array(r)].map(e=>e.toString(16).padStart(2,"0")).join(""),Ba=async r=>Au(await crypto.subtle.digest("SHA-256",r)),za=(r,e=0,t=1)=>Math.max(e,Math.min(t,r));class SE{constructor(e){this.canvas=e,this.canvas.dataset.phase="module-ready",this.renderer=new Yy({canvas:e,antialias:!0,alpha:!1}),this.renderer.setPixelRatio(Math.min(devicePixelRatio,2)),this.renderer.setClearColor(724239,1),this.renderer.outputColorSpace=hn,this.renderer.toneMapping=ql,this.renderer.toneMappingExposure=1.08,this.renderer.shadowMap.enabled=!0,this.renderer.shadowMap.type=jl,this.scene=new J_,this.scene.background=new ot(qi.dark.clear),this.scene.fog=new zo(qi.dark.fog.color,8,24),this.camera=new mn(32,1,.05,100),this.camera.up.set(0,0,1),this.camera.position.set(-1.8,-1.35,1.35),this.controls=new Zy(this.camera,e),this.controls.target.set(0,0,.75),this.controls.enableDamping=!0,this.controls.enablePan=!1,this.controls.minDistance=1.1,this.controls.maxDistance=7,this.controls.minPolarAngle=.15,this.controls.maxPolarAngle=Math.PI*.48,this.controls.rotateSpeed=.72,this.followTarget=new X,this.followDelta=new X,this.cameraFollow=null,this.lastFrameAt=null,this.hemisphere=new sg(14542055,1514013,1.15),this.scene.add(this.hemisphere),this.keyLight=new dl(16773862,2.5),this.keyLight.position.set(-2.5,-3.5,5.5),this.keyLight.castShadow=!0,this.keyLight.shadow.mapSize.set(2048,2048),this.scene.add(this.keyLight),this.rimLight=new dl(16742938,.85),this.rimLight.position.set(3,2,2.8),this.scene.add(this.rimLight),this.objects=[],this.geometryCache=new Map,this.assetBuffers=new Map,this.grid=null,this.raycaster=new lg,this.pointer=new et,this.selectedBody=0,this.selectedHit=new X,this.selectedCenter=new X,this.perturbDrag=null,this.perturbSeq=0,this.lastPerturbSend=0,this.controlDown=!1,this.perturbInFlight=!1,this.queuedPerturb=null,this.clearQueued=!1,this.latestPerturbPayload=null,this.perturbArrow=new hg(new X(1,0,0),new X,.01,Wl,.08,.05),this.perturbArrow.visible=!1,this.scene.add(this.perturbArrow),this.destinationMarker=new _n(new Er(.085,24,16),new ll({color:EE,emissive:6163464,emissiveIntensity:.8,roughness:.28,metalness:.12,transparent:!0,opacity:.48})),this.destinationMarker.castShadow=!0,this.destinationMarker.visible=!1,this.scene.add(this.destinationMarker),this.previous=this.current=null,this.lastSeq=0,this.ready=!1,this.metrics={frames:0,snapshots:0,sequence_gaps:0,bytes:0,render_fps:0,snapshot_hz:0,mean_wire_age_ms:0,authoritative:"python",shadow_physics:!1},window.__MUJOCO_METRICS__=this.metrics,window.__MUJOCO_VIEWPORT__=this,this.onThemeChange=t=>this.applyTheme(t.detail?.theme),window.addEventListener("predactor-theme-change",this.onThemeChange),this.onDestination=t=>this.updateDestinationMarker(t.detail),window.addEventListener("mujoco-destination",this.onDestination),this.applyTheme(document.documentElement.dataset.theme||"dark")}async init(e){if(this.syncPerturbSequence(e.perturb?.accepted_sequence),this.ready){this.verifyHandshake(e);return}if(e.protocol!==1||e.header_bytes!==xr)throw new Error("Unsupported simulation protocol");this.handshake=e,this.cameraFollow=new vE(e.camera,e.root_pose),this.canvas.dataset.phase="assets-loading";const t=await Promise.all(e.files.map(async u=>{const p=await fetch(u.url);if(!p.ok)throw new Error(`Asset fetch failed: ${u.name}`);const f=new Uint8Array(await p.arrayBuffer()),_=await Ba(f);if(_!==u.sha256)throw new Error(`Asset SHA mismatch: ${u.name}`);return{file:u,bytes:f,digest:_}})),n=new TextEncoder().encode(t.map(u=>`${u.file.name}:${u.digest}
`).join(""));if(await Ba(n)!==e.asset_sha256)throw new Error("Asset manifest SHA mismatch");const a=t.find(u=>u.file.name==="model.xml");if(!a||await Ba(a.bytes)!==e.model_sha256)throw new Error("Model SHA mismatch");t.filter(u=>u.file.name.startsWith("mesh/")).forEach(u=>this.assetBuffers.set(u.file.name.slice(5),u.bytes)),this.canvas.dataset.phase="wasm-loading",this.mujoco=await km();const o=new this.mujoco.MjVFS;for(const[u,p]of this.assetBuffers)o.addBuffer(u,p);const l=new TextDecoder().decode(a.bytes).replace(/meshdir="[^"]*"/,'meshdir=""');if(this.model=this.mujoco.MjModel.from_xml_string(l,o),o.delete(),!this.model||this.model.nq!==e.nq||this.model.nv!==e.nv||this.model.nmocap!==e.nmocap||this.model.nuserdata!==e.nuserdata)throw new Error(`Model dimension mismatch: browser ${this.model?.nq}/${this.model?.nv}, server ${e.nq}/${e.nv}`);this.data=new this.mujoco.MjData(this.model),this.option=new this.mujoco.MjvOption,this.perturb=new this.mujoco.MjvPerturb,this.option.geomgroup[3]=0,this.mjCamera=new this.mujoco.MjvCamera,this.mjScene=new this.mujoco.MjvScene(this.model,32768),this.initModelObjects(),this.bindPerturbInteractions(),this.ready=!0,this.canvas.dataset.phase="model-ready",this.startedAt=performance.now(),this.frameWindowAt=this.startedAt,this.animate()}verifyHandshake(e){for(const t of["model_sha256","asset_sha256","nq","nv","nmocap","nuserdata"])if(e[t]!==this.handshake[t])throw new Error(`Reconnect handshake mismatch: ${t}`);if(JSON.stringify(e.camera)!==JSON.stringify(this.handshake.camera))throw new Error("Reconnect handshake mismatch: camera");if(JSON.stringify(e.root_pose)!==JSON.stringify(this.handshake.root_pose))throw new Error("Reconnect handshake mismatch: root pose")}applyTheme(e){this.themeName=e==="light"?"light":"dark";const t=qi[this.themeName];this.renderer.setClearColor(t.clear,1),this.renderer.toneMappingExposure=t.exposure,this.scene.background.setHex(t.clear),this.scene.fog.color.setHex(t.fog.color),this.scene.fog.near=t.fog.near,this.scene.fog.far=t.fog.far,this.hemisphere.color.setHex(t.hemisphere.sky),this.hemisphere.groundColor.setHex(t.hemisphere.ground),this.hemisphere.intensity=t.hemisphere.intensity,this.keyLight.color.setHex(t.key_light.color),this.keyLight.intensity=t.key_light.intensity,this.rimLight.color.setHex(t.rim_light.color),this.rimLight.intensity=t.rim_light.intensity,this.grid&&this.replaceGrid();for(const n of this.objects){const a=n.userData.surfaceRole,o=a==="ground"?t.ground:t.robot[a];o!==void 0&&n.material.color.setHex(o);const l=n.userData.bodyId===this.selectedBody&&this.selectedBody>0;n.material.emissive?.setHex(l?t.selection:0)}this.canvas.dataset.theme=this.themeName,this.metrics&&(this.metrics.theme=this.themeName)}replaceGrid(){this.grid&&(this.scene.remove(this.grid),this.grid.geometry.dispose(),this.grid.material.dispose());const e=qi[this.themeName].grid;this.grid=new ug(200,200,e.center,e.line),this.grid.rotateX(Math.PI/2),this.grid.position.z=.003,this.grid.material.transparent=!0,this.grid.material.opacity=e.opacity,this.scene.add(this.grid)}syncPerturbSequence(e){this.perturbSeq=bu(this.perturbSeq,e)}updateDestinationMarker(e){const t=xE(e);this.destinationMarker.visible=t.visible,t.target&&(this.destinationMarker.position.fromArray(t.target),this.destinationMarker.material.opacity=t.active?1:.48)}accept(e){const t=new DataView(e);if(e.byteLength<xr||String.fromCharCode(...new Uint8Array(e,0,4))!=="MJS1")throw new Error("Invalid snapshot magic");const n=t.getUint16(4,!0),a=t.getUint16(6,!0),o=t.getUint32(8,!0),l=t.getUint32(32,!0),u=t.getUint32(36,!0),p=t.getUint32(40,!0),f=t.getUint32(44,!0);if(n!==1||a!==xr||l!==this.handshake.nq||u!==this.handshake.nv||p!==this.handshake.nmocap||f!==this.handshake.nuserdata)throw new Error("Snapshot schema mismatch");if(Au(e.slice(48,80))!==this.handshake.model_sha256)throw new Error("Snapshot model SHA mismatch");const _=l+u+7*p+f,v=xr+_*8;if(e.byteLength!==v)throw new Error(`Snapshot size mismatch: ${e.byteLength} != ${v}`);this.lastSeq&&o!==this.lastSeq+1&&this.metrics.sequence_gaps++,this.lastSeq=o;let x=xr;const E=m=>{const N=new Float64Array(e.slice(x,x+m*8));return x+=m*8,N},R={seq:o,serverMono:t.getFloat64(16,!0),simTime:t.getFloat64(24,!0),qpos:E(l),qvel:E(u),mocapPos:E(3*p),mocapQuat:E(4*p),userdata:E(f),received:performance.now()};this.current&&R.simTime+1e-9<this.current.simTime?(this.previous=R,this.cameraFollow?.reset(),this.metrics.camera_resets=(this.metrics.camera_resets||0)+1):this.previous=this.current||R,this.current=R,this.metrics.snapshots++,this.metrics.bytes+=e.byteLength;const y=(performance.now()-this.startedAt)/1e3;y>0&&(this.metrics.snapshot_hz=this.metrics.snapshots/y)}geometry(e){const t=`${e.type}:${e.dataid}:${[...e.size].join(",")}`;if(this.geometryCache.has(t))return this.geometryCache.get(t);const n=this.mujoco.mjtGeom;let a;if(e.type===n.mjGEOM_PLANE.value)a=new Cr(200,200);else if(e.type===n.mjGEOM_SPHERE.value)a=new Er(e.size[0],24,16);else if(e.type===n.mjGEOM_CAPSULE.value)a=new Go(e.size[0],2*e.size[2],8,16),a.rotateX(Math.PI/2);else if(e.type===n.mjGEOM_BOX.value)a=new Di(2*e.size[0],2*e.size[1],2*e.size[2]);else if(e.type===n.mjGEOM_CYLINDER.value)a=new Os(e.size[0],e.size[0],2*e.size[2],24),a.rotateX(Math.PI/2);else if(e.type===n.mjGEOM_ELLIPSOID.value)a=new Er(1,24,16),a.scale(...e.size);else if(e.type===n.mjGEOM_MESH.value){const o=e.dataid,l=this.model.mesh_vertadr[o],u=this.model.mesh_vertnum[o],p=this.model.mesh_faceadr[o],f=this.model.mesh_facenum[o],_=Array.from(this.model.mesh_vert.slice(3*l,3*(l+u))),v=Array.from(this.model.mesh_face.slice(3*p,3*(p+f)));a=new cn,a.setAttribute("position",new Nt(_,3)),a.setIndex(v)}else a=new Di(.02,.02,.02);return a.computeVertexNormals(),this.geometryCache.set(t,a),a}initModelObjects(){this.replaceGrid();const e=qi[this.themeName];for(let t=0;t<this.model.ngeom;t++){if(this.model.geom_group[t]===3)continue;const n={type:this.model.geom_type[t],dataid:this.model.geom_dataid[t],size:this.model.geom_size.slice(3*t,3*t+3)},a=this.model.geom_rgba.slice(4*t,4*t+4),o=n.type===this.mujoco.mjtGeom.mjGEOM_PLANE.value,l=this.model.geom_bodyid?.[t]??0,u=o?"ground":l===1?"pelvis":l%2?"odd":"even",p=new ot(u==="ground"?e.ground:e.robot[u]),f=new ll({color:p,roughness:o?.96:.46,metalness:o?0:.42,transparent:a[3]<1,opacity:a[3]}),_=new _n(this.geometry(n),f);_.matrixAutoUpdate=!1,_.castShadow=!o,_.receiveShadow=!0,_.userData.geomId=t,_.userData.bodyId=l,_.userData.surfaceRole=u,this.objects.push(_),this.scene.add(_)}this.applyTheme(this.themeName)}pickBody(e){if(!this.ready||!this.handshake?.perturb?.enabled||e.button!==0)return;const t=this.canvas.getBoundingClientRect();this.pointer.set(2*(e.clientX-t.left)/t.width-1,1-2*(e.clientY-t.top)/t.height),this.raycaster.setFromCamera(this.pointer,this.camera);const n=this.raycaster.intersectObjects(this.objects.filter(o=>o.userData.bodyId>0),!1)[0];if(!n)return;this.selectedBody=n.object.userData.bodyId,this.selectedHit.copy(n.point);for(const o of this.objects){const l=o.userData.bodyId===this.selectedBody;o.material.emissive?.setHex(l?qi[this.themeName].selection:0),o.material.emissiveIntensity=l?.38:0}const a=document.querySelector("#perturb-status");a&&(a.textContent=`BODY ${this.selectedBody} SELECTED`)}perturbPayload(e){const t=this.canvas.getBoundingClientRect(),n=Math.max(40,Math.min(t.width,t.height)*.42),a=za((e.clientX-this.perturbDrag.x)/n,-1,1),o=za((e.clientY-this.perturbDrag.y)/n,-1,1),l=Math.hypot(a,o),u=l>1?[a/l,o/l]:[a,o],p=this.camera.quaternion,f=new X(1,0,0).applyQuaternion(p),_=new X(0,1,0).applyQuaternion(p),v=new X(0,0,-1).applyQuaternion(p);return{protocol:1,command:"set_perturb",seq:++this.perturbSeq,body:this.selectedBody,mode:this.perturbDrag.mode,drag:u,hit:this.selectedHit.toArray(),camera_right:f.toArray(),camera_up:_.toArray(),camera_forward:v.toArray()}}sendPerturb(e){this.latestPerturbPayload=e,this.queuedPerturb=e,this.clearQueued=!1,this.metrics.perturb_sent=(this.metrics.perturb_sent||0)+1,this.updatePerturbVisual(e,"SENDING"),this.pumpPerturb()}async postPerturb(e){const t=await fetch("/api/command",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(e),keepalive:!0});if(!t.ok){const n=await t.json(),a=n.detail,o=new Error(typeof a=="string"?a:a?.code||"Perturb intent rejected");throw o.detail=a,o}return t.json()}async pumpPerturb(){if(this.perturbInFlight)return;const e=this.clearQueued&&!this.queuedPerturb,t=e?{protocol:1,command:"clear_perturb"}:this.queuedPerturb;if(t){e?this.clearQueued=!1:this.queuedPerturb=null,this.perturbInFlight=!0;try{const n=await this.postPerturb(t);e?this.canvas.dataset.perturbTransport="clear":(this.metrics.perturb_acked=(this.metrics.perturb_acked||0)+1,this.syncPerturbSequence(t.seq),this.canvas.dataset.perturbTransport="acked",this.canvas.dataset.perturbSequence=String(t.seq),uE(this.perturbDrag,this.latestPerturbPayload,t)&&this.updatePerturbVisual(t,"ACK")),this.lastPerturbState=n.perturb}catch(n){if(this.metrics.perturb_rejected=(this.metrics.perturb_rejected||0)+1,this.canvas.dataset.perturbTransport="rejected",!e&&n.detail?.code==="stale_perturb_sequence"&&this.perturbDrag&&!this.perturbDrag.staleRetried){this.perturbDrag.staleRetried=!0,this.syncPerturbSequence(n.detail.current_sequence);const o=hE(this.latestPerturbPayload||t,n.detail.current_sequence);this.perturbSeq=o.seq,this.latestPerturbPayload=o,this.queuedPerturb=o,this.updatePerturbVisual(o,"RESYNC")}else{const o=document.querySelector("#perturb-status");o&&(o.textContent=this.perturbDrag?"PERTURB RETRY ON MOVE":"PERTURB REJECTED"),Po(n)}}finally{this.perturbInFlight=!1,(this.queuedPerturb||this.clearQueued)&&this.pumpPerturb()}}}updatePerturbVisual(e,t){const n=e.drag,a=Math.hypot(...n),o=new X(...e.camera_right),l=new X(...e.camera_up),u=e.mode==="force"?o.multiplyScalar(n[0]).addScaledVector(l,-n[1]):o.multiplyScalar(-n[1]).addScaledVector(l,n[0]);this.updateSelectedBodyCenter(),this.perturbArrow.setColor(new ot(e.mode==="force"?Wl:yE)),a>.005&&(this.perturbArrow.setDirection(u.normalize()),this.perturbArrow.setLength(.16+.72*a,.1,.06)),this.perturbArrow.visible=dE(this.perturbDrag,a);const p=document.querySelector("#perturb-status");p&&(p.textContent=`${e.mode.toUpperCase()} ${t} · ${Math.round(a*100)}% · #${e.seq}`)}updateSelectedBodyCenter(){const e=fE(this.data?.xpos,this.selectedBody);e&&(this.selectedCenter.fromArray(e),this.perturbArrow.position.copy(this.selectedCenter))}clearPerturb(){const e=!!this.perturbDrag;this.perturbDrag=null,this.latestPerturbPayload=null,this.controls.enabled=!0,this.perturbArrow.visible=!1,this.queuedPerturb=null,(e||this.perturbInFlight)&&(this.clearQueued=!0,this.pumpPerturb());const t=document.querySelector("#perturb-status");t&&this.selectedBody&&(t.textContent=`BODY ${this.selectedBody} SELECTED`)}bindPerturbInteractions(){this.canvas.addEventListener("dblclick",e=>this.pickBody(e)),this.canvas.addEventListener("pointerdown",e=>{if(!(e.ctrlKey||this.controlDown)||!this.selectedBody||!this.handshake?.perturb?.enabled||![0,2].includes(e.button))return;e.preventDefault(),e.stopImmediatePropagation(),this.controls.enabled=!1,this.perturbDrag={pointerId:e.pointerId,x:e.clientX,y:e.clientY,mode:e.button===2?"force":"torque",visualStarted:!1,staleRetried:!1},this.lastPerturbSend=0,this.canvas.setPointerCapture(e.pointerId);const t=document.querySelector("#perturb-status");t&&(t.textContent=`${this.perturbDrag.mode.toUpperCase()} DRAG`)},!0),this.canvas.addEventListener("pointermove",e=>{if(!this.perturbDrag||e.pointerId!==this.perturbDrag.pointerId)return;e.preventDefault(),e.stopImmediatePropagation();const t=performance.now();t-this.lastPerturbSend<30||(this.lastPerturbSend=t,this.sendPerturb(this.perturbPayload(e)))},!0);for(const e of["pointerup","pointercancel"])window.addEventListener(e,t=>{this.perturbDrag&&t.pointerId===this.perturbDrag.pointerId&&(t.preventDefault(),t.stopImmediatePropagation(),this.clearPerturb())},!0);this.canvas.addEventListener("lostpointercapture",e=>{!this.perturbDrag||e.pointerId!==this.perturbDrag.pointerId||e.buttons===0||queueMicrotask(()=>{this.perturbDrag?.pointerId===e.pointerId&&!this.canvas.hasPointerCapture(e.pointerId)&&this.canvas.setPointerCapture(e.pointerId)})}),this.canvas.addEventListener("contextmenu",e=>{e.ctrlKey&&e.preventDefault()}),window.addEventListener("keydown",e=>{e.key==="Control"&&(this.controlDown=!0)},!0),window.addEventListener("keyup",e=>{e.key==="Control"&&(this.controlDown=!1)},!0),window.addEventListener("blur",()=>{this.controlDown=!1,this.clearPerturb()}),window.addEventListener("mujoco-perturb-clear",()=>this.clearPerturb()),window.addEventListener("mujoco-perturb-sequence",e=>this.syncPerturbSequence(e.detail))}followPelvis(e){if(!this.cameraFollow)return;const t=this.cameraFollow.update(this.data.qpos,this.camera.position.toArray(),this.controls.target.toArray(),e);t.applied&&(this.camera.position.fromArray(t.camera),this.followTarget.fromArray(t.target),this.controls.target.copy(this.followTarget),this.canvas.dataset.cameraYawDelta=String(t.yaw_delta))}updateScene(){this.mujoco.mjv_updateScene(this.model,this.data,this.option,this.perturb,this.mjCamera,this.mujoco.mjtCatBit.mjCAT_ALL.value,this.mjScene),this.mjScene.geoms.delete();for(const t of this.objects){const n=t.userData.geomId,a=this.data.geom_xpos,o=this.data.geom_xmat,l=3*n,u=9*n;t.matrix.set(o[u],o[u+1],o[u+2],a[l],o[u+3],o[u+4],o[u+5],a[l+1],o[u+6],o[u+7],o[u+8],a[l+2],0,0,0,1),t.matrixWorldNeedsUpdate=!0}}animate(){const e=t=>{try{const n=this.lastFrameAt===null?0:(t-this.lastFrameAt)/1e3;this.lastFrameAt=t;const a=this.canvas.getBoundingClientRect(),o=Math.max(2,a.width),l=Math.max(2,a.height);if((this.canvas.width!==Math.round(o*devicePixelRatio)||this.canvas.height!==Math.round(l*devicePixelRatio))&&(this.renderer.setSize(o,l,!1),this.camera.aspect=o/l,this.camera.updateProjectionMatrix()),this.current){const u=this.previous,p=Math.max(1,this.current.received-u.received),f=za((t-(this.current.received-p))/p);for(let _=0;_<this.model.nq;_++)this.data.qpos[_]=u.qpos[_]+(this.current.qpos[_]-u.qpos[_])*f;for(let _=0;_<this.model.nv;_++)this.data.qvel[_]=u.qvel[_]+(this.current.qvel[_]-u.qvel[_])*f;gE(this.data.qpos,u.qpos,this.current.qpos,f,this.handshake.root_pose),this.data.time=u.simTime+(this.current.simTime-u.simTime)*f,this.data.mocap_pos.set(this.current.mocapPos),this.data.mocap_quat.set(this.current.mocapQuat),this.data.userdata.set(this.current.userdata),this.mujoco.mj_forward(this.model,this.data),this.updateScene(),this.updateSelectedBodyCenter(),this.followPelvis(n)}this.controls.update(),this.renderer.render(this.scene,this.camera),this.metrics.frames++,t-this.frameWindowAt>=1e3&&(this.metrics.render_fps=this.metrics.frames*1e3/(t-this.startedAt),this.canvas.dataset.renderFps=this.metrics.render_fps.toFixed(1),this.canvas.dataset.snapshotHz=this.metrics.snapshot_hz.toFixed(1),this.canvas.dataset.sequenceGaps=String(this.metrics.sequence_gaps),this.frameWindowAt=t),!this.firstFrame&&this.current&&(this.firstFrame=!0,this.canvas.dataset.phase="rendering",window.dispatchEvent(new Event("mujoco-frame")))}catch(n){Po(n);return}requestAnimationFrame(e)};requestAnimationFrame(e)}}const ri=new SE(document.querySelector("#sim-canvas"));let Ru;function Cu(){const r=new WebSocket(`${location.protocol==="https:"?"wss":"ws"}://${location.host}/ws/sim`);r.binaryType="arraybuffer",r.onmessage=async e=>{try{if(typeof e.data=="string"){const t=JSON.parse(e.data);await ri.init(t),r.send(JSON.stringify({protocol:1,kind:"ready",model_sha256:t.model_sha256}))}else ri.accept(e.data)}catch(t){Po(t),r.close(4002,"validation failed")}},r.onclose=e=>{ri.clearPerturb(),e.code!==4002&&(Ru=setTimeout(Cu,900))},r.onerror=()=>r.close()}Cu();window.addEventListener("beforeunload",()=>{clearTimeout(Ru),ri.clearPerturb(),window.removeEventListener("predactor-theme-change",ri.onThemeChange),window.removeEventListener("mujoco-destination",ri.onDestination),ri.controls.dispose(),ri.renderer.dispose()});const ME=Object.freeze(Object.defineProperty({__proto__:null},Symbol.toStringTag,{value:"Module"}));
