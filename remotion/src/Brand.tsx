// 頻道美術（選配）：頭像 800×800、橫幅 2560×1440（手機安全區 1546×423 置中）、橫式 logo 1600×500。米白紙＋黑油墨＋紅印章。
// npx remotion still src/index.ts BrandAvatar avatar.png --props='{"name":"頻道名","mark":"印章","tagline":"一句話","note":"每天早上更新"}'
import React from 'react';
import {AbsoluteFill} from 'remotion';

const INK = '#141210', PAPER = '#F3EEE3', RED = '#B3261E';
const F = 'NotoTC, "PingFang TC", "Noto Sans CJK TC", "Microsoft JhengHei", sans-serif';
export type BrandProps = {name: string; mark: string; tagline: string; note?: string};
const Paper: React.FC<{children: React.ReactNode}> = ({children}) => (
	<AbsoluteFill style={{background: PAPER, fontFamily: F, color: INK}}>
		<AbsoluteFill style={{backgroundImage: 'radial-gradient(#00000012 1.2px, transparent 1.4px)', backgroundSize: '7px 7px'}} />
		{children}
	</AbsoluteFill>
);
// 小走勢線：先跌後漲，結尾一個紅點
const Spark: React.FC<{w: number; h: number; sw: number}> = ({w, h, sw}) => (
	<svg width={w} height={h} viewBox="0 0 300 100">
		<polyline points="0,40 40,58 80,46 120,78 160,62 200,70 240,30 290,12" fill="none" stroke={INK} strokeWidth={sw} strokeLinejoin="round" strokeLinecap="round" />
		<circle cx={290} cy={12} r={sw * 1.6} fill={RED} />
	</svg>
);

export const Avatar: React.FC<BrandProps> = ({mark}) => (
	<Paper>
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
			{/* 圓形頭像會被裁：內容都在中間 600 px 內 */}
			<div style={{width: 600, height: 600, borderRadius: '50%', border: `14px double ${RED}`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', transform: 'rotate(-6deg)'}}>
				<div style={{fontSize: mark.length > 2 ? 150 : 210, fontWeight: 900, lineHeight: 1, color: INK, letterSpacing: 6}}>{mark}</div>
				<div style={{marginTop: 26}}><Spark w={300} h={100} sw={11} /></div>
			</div>
		</AbsoluteFill>
	</Paper>
);

export const Banner: React.FC<BrandProps> = ({name, tagline, note}) => (
	<Paper>
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
			<div style={{width: 1546, height: 423, borderTop: `12px solid ${INK}`, borderBottom: `4px solid ${INK}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 30px'}}>
				<div>
					<div style={{fontSize: 150, fontWeight: 900, letterSpacing: 10, lineHeight: 1.1}}>{name}</div>
					<div style={{fontSize: 44, fontWeight: 700, color: '#5C564C', marginTop: 10}}>{tagline}</div>
				</div>
				<div style={{display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 18}}>
					<Spark w={360} h={120} sw={10} />
					{note && <div style={{border: `6px solid ${RED}`, color: RED, fontSize: 40, fontWeight: 900, padding: '4px 22px', transform: 'rotate(-5deg)'}}>{note}</div>}
				</div>
			</div>
		</AbsoluteFill>
	</Paper>
);

export const Logo: React.FC<BrandProps> = ({name, mark}) => (
	<Paper>
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 50}}>
			<div style={{width: 300, height: 300, borderRadius: '50%', border: `10px double ${RED}`, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: 'rotate(-6deg)'}}>
				<span style={{fontSize: mark.length > 2 ? 80 : 110, fontWeight: 900}}>{mark}</span>
			</div>
			<div style={{borderTop: `10px solid ${INK}`, borderBottom: `3px solid ${INK}`, padding: '10px 0'}}>
				<div style={{fontSize: 140, fontWeight: 900, letterSpacing: 8, lineHeight: 1.1}}>{name}</div>
			</div>
		</AbsoluteFill>
	</Paper>
);
