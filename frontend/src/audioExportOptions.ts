export function formatAudioBytes(bytes:number|null|undefined):string {
 if(bytes===null||bytes===undefined||!Number.isFinite(bytes)||bytes<0)return 'No disponible';
 if(bytes>=1e9)return `${(bytes/1e9).toFixed(2)} GB`;
 if(bytes>=1e6)return `${(bytes/1e6).toFixed(1)} MB`;
 return `${(bytes/1e3).toFixed(1)} kB`;
}
export function estimatedMp3Bytes(duration:number,kbps:number):number{return Math.round(Math.max(0,duration)*kbps*1000/8)}
