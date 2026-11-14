import React from 'react';
import {Composition, continueRender, delayRender, staticFile} from 'remotion';
import {Daily, Episode, totalFrames} from './Video';
import {Avatar, Banner, Logo, BrandProps} from './Brand';

// 字型：remotion/public/fonts/ 有 Noto Sans CJK TC（python3 tools/get_fonts.py 下載）就用它；沒有就退回系統的中文字型
const W = [400, 500, 700, 900] as const;
const files = {400: 'Regular', 500: 'Medium', 700: 'Bold', 900: 'Black'} as const;
const h = delayRender('fonts');
Promise.all(W.map((w) => new FontFace('NotoTC', `url(${staticFile(`fonts/NotoSansCJKtc-${files[w]}.otf`)})`, {weight: String(w)}).load()
	.then((f) => (document.fonts as any).add(f)).catch(() => null))).then(() => continueRender(h));

const brand = {name: '頻道名', mark: '印章', tagline: '一句話介紹', note: ''} as BrandProps;

// Daily 的 props 由 tools/make_day.py 用 --props 傳進來（work/<集>/props.json）
export const Root: React.FC = () => (
	<>
	<Composition id="BrandAvatar" component={Avatar} fps={30} width={800} height={800} durationInFrames={1} defaultProps={brand} />
	<Composition id="BrandBanner" component={Banner} fps={30} width={2560} height={1440} durationInFrames={1} defaultProps={brand} />
	<Composition id="BrandLogo" component={Logo} fps={30} width={1600} height={500} durationInFrames={1} defaultProps={brand} />
	<Composition
		id="Daily"
		component={Daily}
		fps={30}
		width={1920}
		height={1080}
		durationInFrames={300}
		defaultProps={{ep: null as unknown as Episode}}
		calculateMetadata={({props}) => ({durationInFrames: props.ep ? totalFrames(props.ep) : 300})}
	/>
	</>
);
