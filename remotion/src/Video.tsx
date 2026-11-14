// 一集的動畫版型（片頭 → 各段 → 片尾）。資料全部來自 tools/make_day.py 產生的 props.json；
// 頻道名、圖卡文字、配色、判定印章的字都從主題（themes/<主題>/theme.json）帶進來，這個檔不寫死任何主題內容。
import React from 'react';
import {AbsoluteFill, Easing, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';

export type Row = {name: string; ticker: string; aliases?: string[]; close: number; chg: number; series: [string, number][]};
export type Section = {title: string; sub?: string; kind: 'open' | 'market' | 'points'; lines: string[]};
export type Cue = {sec: number; line: number; text: string; t0: number; t1: number};
export type EventCard = {label: string; head: string; body: string; num?: {text: string; dir: 'up' | 'down' | 'flat'} | null; source: string;
	ticker?: string | null; name?: string | null; stock?: {close: number; chg: number; label: string; series: [string, number][]}};
export type TodayChart = {title: string; type: 'bar' | 'line'; unit: string; points: [string, number][]; source: string};
export type Theme = {
	text: Record<string, string>;
	verdict?: {prefix: string; options: Record<string, string>} | null;
	trend_words: {up: string[]; down: string[]};
	palette: {bg: string; bg2: string; panel: string; ink: string; muted: string; accent: string; up: string; down: string};
};
export type Episode = {
	day: string; channel: string; stamp?: string; intro_line?: boolean; headline?: string; badge?: string | null; accent?: string; range?: string | null; tagline: string;
	intro: number; outro: number; narration: number; vo: string;
	jingle?: {intro: string; outro: string; intro_hit?: number; outro_hit?: number} | null;
	sections: Section[]; cues: Cue[]; burn_subs?: boolean; events?: Record<string, EventCard>; chart?: TodayChart | null;
	market?: {as_of: string; rows: Row[]; chg_label?: string; default?: number} | null;
	theme: Theme;
};

// 這些在 <Daily> 一開始由 applyTheme() 換成主題的值
const C = {bg: '#F3EEE3', bg2: '#E9E2D2', panel: '#FBF8F1', line: '#141210', teal: '#1D3557', txt: '#141210', muted: '#5C564C', up: '#1F6B3A', down: '#B3261E'};
let INK = '#141210', PAPER = '#F3EEE3';
let TX: Record<string, string> = {};
let UPW: string[] = [], DOWNW: string[] = [];
let TOK = /([+-]?\d[\d,]*(?:\.\d+)?%)/;
let VERDICT: Record<string, string> = {};
let VERDICT_RE: RegExp | null = null;
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const byLen = (a: string[]) => [...a].sort((x, y) => y.length - x.length);

const applyTheme = (ep: Episode) => {
	const p = ep.theme.palette;
	Object.assign(C, {bg: p.bg, bg2: p.bg2, panel: p.panel, line: p.ink, txt: p.ink, muted: p.muted, up: p.up, down: p.down, teal: ep.accent ?? p.accent});
	INK = p.ink; PAPER = p.bg; TX = ep.theme.text;
	UPW = ep.theme.trend_words.up; DOWNW = ep.theme.trend_words.down;
	TOK = new RegExp(`([+-]?\\d[\\d,]*(?:\\.\\d+)?%${byLen([...UPW, ...DOWNW]).map((w) => '|' + esc(w)).join('')})`);
	VERDICT = ep.theme.verdict?.options ?? {};
	const opts = byLen(Object.keys(VERDICT)).map(esc).join('|');
	VERDICT_RE = ep.theme.verdict && opts ? new RegExp(`${esc(ep.theme.verdict.prefix)}[：:]\\s*(${opts})[。．.，,]?\\s*`) : null;
};
const tx = (k: string, vars: Record<string, string | number> = {}) => (TX[k] ?? '').replace(/\{(\w+)\}/g, (_, v) => String(vars[v] ?? ''));

const FONT = 'NotoTC, "PingFang TC", "Noto Sans CJK TC", "Microsoft JhengHei", sans-serif';
const FPS = 30;
const f = (s: number) => Math.round(s * FPS);
export const totalFrames = (ep: Episode) => f(ep.intro + ep.narration + 0.6 + ep.outro);

// 方向字（上漲／下跌…）上色；% 數字跟著前面最近的方向字（有 +/- 號以號為準）
const Colored: React.FC<{text: string; base?: string}> = ({text, base = C.txt}) => {
	let trend: string | null = null;
	return (
		<>
			{text.split(TOK).filter(Boolean).map((t, i) => {
				let c = base;
				if (UPW.includes(t)) trend = c = C.up;
				else if (DOWNW.includes(t)) trend = c = C.down;
				else if (t.endsWith('%')) c = t.startsWith('-') ? C.down : t.startsWith('+') ? C.up : trend ?? base;
				return <span key={i} style={{color: c}}>{t}</span>;
			})}
		</>
	);
};

// ───────── 判定印章：「判定：同意。」這種句子開頭 → 蓋一個有顏色的章（字與顏色在主題的 verdict）─────────
const verdictOf = (line: string) => (VERDICT_RE ? line.match(VERDICT_RE)?.[1] : undefined);
const stripVerdict = (line: string) => (VERDICT_RE ? line.replace(VERDICT_RE, '') : line);
const VerdictTag: React.FC<{v: string; big?: boolean; pop?: number}> = ({v, big, pop = 1}) => (
	<span style={{display: 'inline-block', padding: big ? '6px 30px' : '0 12px', marginRight: 16, border: `${big ? 8 : 4}px ${big ? 'double' : 'solid'} ${VERDICT[v]}`,
		color: VERDICT[v], fontWeight: 900, fontSize: big ? 72 : 36, letterSpacing: big ? 6 : 2, borderRadius: 8, opacity: 0.9,
		transform: `scale(${pop}) rotate(${big ? -7 : -2}deg)`, background: `${PAPER}cc`}}>{v}</span>
);

// ───────── 背景：紙張漸層＋慢慢漂移的網點（畫面永遠在動）─────────
const Backdrop: React.FC = () => {
	const fr = useCurrentFrame();
	const gx = 50 + 18 * Math.sin(fr / 140), gy = 40 + 12 * Math.cos(fr / 170);
	return (
		<AbsoluteFill style={{background: `radial-gradient(1400px 900px at ${gx}% ${gy}%, ${C.panel} 0%, ${C.bg} 55%, ${C.bg2} 100%)`}}>
			<AbsoluteFill style={{backgroundImage: 'radial-gradient(#0000000f 1px, transparent 1.2px)', backgroundSize: '6px 6px', backgroundPosition: `${(fr * 0.15) % 6}px 0px`}} />
		</AbsoluteFill>
	);
};

// ───────── 片頭：上下拉線 → 印章蓋下（對準片頭音效的重拍 intro_hit）→ 頻道名逐字彈出 ─────────
const Stamp: React.FC<{text: string; size: number; scale?: number; opacity?: number}> = ({text, size, scale = 1, opacity = 1}) => (
	<div style={{width: size, height: size, borderRadius: '50%', border: `${Math.round(size / 20)}px double ${C.down}`, color: C.down, display: 'flex', alignItems: 'center', justifyContent: 'center',
		fontSize: size * (text.length > 2 ? 0.28 : 0.36), fontWeight: 900, whiteSpace: 'nowrap', transform: `rotate(-9deg) scale(${scale})`, opacity, background: `${PAPER}dd`, flexShrink: 0}}>{text}</div>
);

const Intro: React.FC<{ep: Episode}> = ({ep}) => {
	const fr = useCurrentFrame(); const {fps} = useVideoConfig();
	const hit = f(ep.jingle?.intro_hit ?? 0.6);
	const rule = interpolate(fr, [0, hit], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
	const s = interpolate(fr, [hit - 6, hit, hit + 5], [3.2, 0.9, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)});
	const so = interpolate(fr, [hit - 6, hit - 2], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const shake = fr >= hit && fr < hit + 7 ? Math.sin((fr - hit) * 2.6) * (7 - (fr - hit)) * 1.6 : 0;
	const ring = interpolate(fr, [hit, hit + 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
	const word = Array.from(ep.channel);
	const size = word.length > 6 ? Math.floor(170 * 6 / word.length) : 170;
	const line = interpolate(fr, [hit + 22, hit + 50], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
	const tag = interpolate(fr, [hit + 40, hit + 54], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const out = interpolate(fr, [f(ep.intro) - 8, f(ep.intro)], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{fontFamily: FONT, opacity: out, alignItems: 'center', justifyContent: 'center', transform: `translate(${shake}px, ${shake * 0.6}px)`}}>
			<div style={{position: 'absolute', top: 300, height: 12, background: INK, width: `${rule * 1680}px`}} />
			<div style={{position: 'absolute', top: 790, height: 4, background: INK, width: `${rule * 1680}px`}} />
			<div style={{display: 'flex', alignItems: 'center', gap: 70}}>
				{ep.stamp && <div style={{position: 'relative', width: 330, height: 330}}>
					<div style={{position: 'absolute', inset: -40 * ring, borderRadius: '50%', border: `${6 * (1 - ring)}px solid ${C.down}`, opacity: 1 - ring}} />
					<Stamp text={ep.stamp} size={330} scale={s} opacity={so * 0.94} />
				</div>}
				<div>
					<div style={{display: 'flex', fontSize: size, fontWeight: 900, color: INK, letterSpacing: 10}}>
						{word.map((ch, i) => {
							const a = spring({frame: fr - hit - 6 - i * 3, fps, config: {damping: 14}});
							return <span key={i} style={{display: 'inline-block', transform: `translateY(${(1 - a) * 60}px)`, opacity: a}}>{ch}</span>;
						})}
					</div>
					{/* 頻道名下面的走勢折線：主題的 intro_line 決定畫不畫（預設只有開了市場資料的主題才畫）；不畫就換成一條底線 */}
					{ep.intro_line ? <svg width={760} height={110} viewBox="0 0 760 110" style={{marginTop: 6}}>
						<polyline points="0,70 90,86 170,62 260,92 350,58 440,74 540,36 640,48 740,14" fill="none" stroke={INK} strokeWidth={9} strokeLinejoin="round" strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={line} />
						<circle cx={740} cy={14} r={13 * (1 - line)} fill={C.down} />
					</svg> : <div style={{height: 10, marginTop: 24, background: C.teal, width: `${(1 - line) * 100}%`}} />}
				</div>
			</div>
			<div style={{position: 'absolute', top: 820, display: 'flex', gap: 40, alignItems: 'center', opacity: tag, fontSize: 44, fontWeight: 700, color: C.muted}}>
				<span>{ep.tagline}</span>
				{ep.badge && <span style={{background: INK, color: PAPER, padding: '4px 26px', fontWeight: 900}}>{ep.badge}</span>}
				<span>{ep.range ?? ep.day.replace(/-/g, '/')}</span>
			</div>
		</AbsoluteFill>
	);
};

// ───────── 片尾：提醒句＋訂閱按下去＋小鈴鐺搖 ─────────
const Bell: React.FC<{rot: number}> = ({rot}) => (
	<svg width={110} height={110} viewBox="0 0 24 24" style={{transform: `rotate(${rot}deg)`, transformOrigin: '50% 10%'}}>
		<path fill={C.txt} d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2Z" />
	</svg>
);

const Outro: React.FC<{ep: Episode}> = ({ep}) => {
	const fr = useCurrentFrame();
	const {fps} = useVideoConfig();
	const a = spring({frame: fr, fps, config: {damping: 16}});
	const btn = spring({frame: fr - 25, fps, config: {damping: 10}});
	const press = fr >= 55 && fr < 62 ? 0.92 : 1;
	const subscribed = fr >= 58;
	const hb = f(ep.jingle?.outro_hit ?? 1.2) + 10;                         // 鈴鐺跟片尾音效的重拍一起搖
	const bell = spring({frame: fr - hb, fps, config: {damping: 14}});
	const ring = fr > hb ? 22 * Math.sin((fr - hb) / 2.2) * Math.exp(-(fr - hb) / 22) : 0;
	const logo = interpolate(fr, [0, 8, 13], [2.4, 0.92, 1], {extrapolateRight: 'clamp'});
	const fade = interpolate(fr, [f(ep.outro) - 10, f(ep.outro)], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', fontFamily: FONT, opacity: fade}}>
			<div style={{display: 'flex', alignItems: 'center', gap: 30, marginBottom: 50}}>
				{ep.stamp && <Stamp text={ep.stamp} size={150} scale={logo} />}
				<div style={{fontSize: 96, fontWeight: 900, color: INK, letterSpacing: 8}}>{ep.channel}</div>
			</div>
			<div style={{fontSize: 64, fontWeight: 900, color: C.txt, opacity: a, transform: `translateY(${(1 - a) * 40}px)`}}>{tx('outro_line')}</div>
			<div style={{display: 'flex', alignItems: 'center', gap: 50, marginTop: 70}}>
				<div style={{
					padding: '26px 70px', borderRadius: 999, fontSize: 56, fontWeight: 900, transform: `scale(${btn * press})`,
					background: subscribed ? C.panel : C.teal, color: subscribed ? C.teal : C.bg, border: `4px solid ${C.teal}`,
				}}>{subscribed ? tx('subscribed') : tx('subscribe', {channel: ep.channel})}</div>
				<div style={{opacity: bell, transform: `scale(${bell})`}}><Bell rot={ring} /></div>
			</div>
			<div style={{fontSize: 42, fontWeight: 500, color: C.muted, marginTop: 50, opacity: interpolate(fr, [40, 60], [0, 1], {extrapolateRight: 'clamp'})}}>{tx('outro_note')}</div>
		</AbsoluteFill>
	);
};

// ───────── 上方：頻道名＋日期＋章節進度 ─────────
const TopBar: React.FC<{ep: Episode; t: number}> = ({ep, t}) => {
	const starts = ep.sections.map((_, i) => ep.cues.find((c) => c.sec === i)?.t0 ?? 0);
	return (
		<div style={{position: 'absolute', top: 30, left: 90, right: 90, fontFamily: FONT, borderTop: `6px solid ${INK}`, paddingTop: 6}}>
			<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontSize: 30, borderBottom: `2px solid ${INK}`, paddingBottom: 6}}>
				<span style={{color: INK, fontWeight: 900, fontSize: 40, letterSpacing: 4}}>{ep.channel}{ep.badge && <span style={{marginLeft: 18, padding: '0 14px', background: INK, color: PAPER, fontWeight: 900, fontSize: 32}}>{ep.badge}</span>}</span>
				<span style={{color: C.muted, fontWeight: 700}}>{ep.range ?? ep.day.replace(/-/g, '/')}</span>
			</div>
			<div style={{display: 'flex', gap: 8, marginTop: 14}}>
				{ep.sections.map((s, i) => {
					const a = starts[i], b = starts[i + 1] ?? ep.narration;
					const p = Math.max(0, Math.min(1, (t - a) / (b - a)));
					return <div key={i} style={{flex: b - a, height: 6, borderRadius: 3, background: `${C.line}33`, overflow: 'hidden'}}>
						<div style={{width: `${p * 100}%`, height: '100%', background: C.teal}} />
					</div>;
				})}
			</div>
		</div>
	);
};

// ───────── 下方：跑馬燈（主題有市場資料才有）＋字幕 ─────────
const Ticker: React.FC<{rows: Row[]}> = ({rows}) => {
	const fr = useCurrentFrame();
	const items = [...rows, ...rows, ...rows, ...rows];
	const unit = 600;
	return (
		<div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: 64, background: INK, borderTop: `3px solid ${C.teal}`, overflow: 'hidden', fontFamily: FONT}}>
			<div style={{display: 'flex', transform: `translateX(${-((fr * 2.2) % (unit * rows.length))}px)`, whiteSpace: 'nowrap'}}>
				{items.map((r, i) => (
					<div key={i} style={{width: unit, flexShrink: 0, fontSize: 30, lineHeight: '64px', paddingLeft: 40, color: PAPER, fontWeight: 700, borderLeft: '2px solid #ffffff33'}}>
						{r.name}　{r.close.toLocaleString('en-US', {maximumFractionDigits: 2})}
						<span style={{color: r.chg >= 0 ? '#5BD38A' : '#FF6B5E'}}>{r.chg >= 0 ? '▲' : '▼'} {Math.abs(r.chg).toFixed(2)}%</span>
					</div>
				))}
			</div>
		</div>
	);
};

const Subtitle: React.FC<{cue?: Cue; t: number; bottom: number}> = ({cue, t, bottom}) => {
	if (!cue) return null;
	const a = interpolate(t - cue.t0, [0, 0.18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<div style={{position: 'absolute', bottom, left: 140, right: 140, display: 'flex', justifyContent: 'center', fontFamily: FONT}}>
			<div style={{background: `${INK}ee`, borderRadius: 4, padding: '16px 36px', fontSize: 50, fontWeight: 700, color: PAPER, textAlign: 'center', lineHeight: 1.45, opacity: a, transform: `translateY(${(1 - a) * 12}px)`}}>
				{cue.text}
			</div>
		</div>
	);
};

// ───────── 走勢線：每換一個指數就重畫一次 ─────────
const Chart: React.FC<{row: Row; since: number; t: number; asOf: string}> = ({row, since, t, asOf}) => {
	const W = 1740, H = 320, L = 130, R = 40, T = 70, B = 46;
	const v = row.series.map((s) => s[1]);
	let lo = Math.min(...v), hi = Math.max(...v);
	const pad = (hi - lo) * 0.12 || 1; lo -= pad; hi += pad;
	const pts = v.map((y, i) => [L + (i * (W - L - R)) / (v.length - 1), T + ((hi - y) / (hi - lo)) * (H - T - B)]);
	const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
	const draw = interpolate(t - since, [0, 1.6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
	const col = v[v.length - 1] >= v[0] ? C.up : C.down;
	const n = Math.max(1, Math.round(draw * (pts.length - 1)));
	const head = pts[n];
	const pulse = 1 + 0.35 * Math.abs(Math.sin(t * 3));
	return (
		<svg width={W} height={H} style={{background: C.panel, border: `2px solid ${INK}`}}>
			<defs><pattern id="fill" width="8" height="8" patternUnits="userSpaceOnUse"><circle cx="4" cy="4" r="1.9" fill={col} opacity={0.55} /></pattern></defs>
			<text x={30} y={46} fill={C.txt} fontSize={30} fontWeight={700} fontFamily={FONT}>{row.name}｜{tx('chart_days', {n: v.length})}</text>
			<text x={W - R} y={44} fill={C.muted} fontSize={22} textAnchor="end" fontFamily={FONT}>{tx('data_source')}（{asOf}）</text>
			{[0, 1, 2, 3].map((k) => {
				const y = T + (k * (H - T - B)) / 3;
				return <g key={k}><line x1={L} x2={W - R} y1={y} y2={y} stroke={C.line} /><text x={L - 14} y={y + 8} fill={C.muted} fontSize={22} textAnchor="end" fontFamily={FONT}>{(hi - (k * (hi - lo)) / 3).toLocaleString('en-US', {maximumFractionDigits: 0})}</text></g>;
			})}
			<path d={`${d} L${pts[pts.length - 1][0]},${H - B} L${L},${H - B} Z`} fill="url(#fill)" style={{clipPath: `inset(0 ${(1 - draw) * 100}% 0 0)`}} />
			<path d={d} fill="none" stroke={INK} strokeWidth={5} strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
			<circle cx={head[0]} cy={head[1]} r={10 * (draw >= 1 ? pulse : 1)} fill={col} />
			<text x={L} y={H - 12} fill={C.muted} fontSize={22} fontFamily={FONT}>{row.series[0][0].slice(5)}</text>
			<text x={W - R} y={H - 12} fill={C.muted} fontSize={22} textAnchor="end" fontFamily={FONT}>{row.series[row.series.length - 1][0].slice(5)}</text>
		</svg>
	);
};

// ───────── 大事圖卡（左＝大標＋內文，右＝大數字＋真實走勢，底＝出處）─────────
const MiniLine: React.FC<{series: [string, number][]; since: number; t: number; w: number; h: number}> = ({series, since, t, w, h}) => {
	const v = series.map((s) => s[1]); const lo = Math.min(...v), hi = Math.max(...v);
	const pts = v.map((y, i) => [10 + (i * (w - 20)) / (v.length - 1), 10 + ((hi - y) / (hi - lo || 1)) * (h - 20)]);
	const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
	const g = interpolate(t - since, [0.2, 1.6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
	const col = v[v.length - 1] >= v[0] ? C.up : C.down;
	const head = pts[Math.max(0, Math.round(g * (pts.length - 1)))];
	return (
		<svg width={w} height={h}>
			<defs><pattern id="evfill" width="7" height="7" patternUnits="userSpaceOnUse"><circle cx="3.5" cy="3.5" r="1.6" fill={col} opacity={0.5} /></pattern></defs>
			<path d={`${d} L${pts[pts.length - 1][0]},${h} L10,${h} Z`} fill="url(#evfill)" style={{clipPath: `inset(0 ${(1 - g) * 100}% 0 0)`}} />
			<path d={d} fill="none" stroke={INK} strokeWidth={4} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - g} strokeLinejoin="round" />
			<circle cx={head[0]} cy={head[1]} r={8} fill={col} />
		</svg>
	);
};

const EventCardView: React.FC<{e: EventCard; since: number; t: number}> = ({e, since, t}) => {
	const a = interpolate(t - since, [0, 0.45], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
	const stamp = interpolate(t - since, [0.15, 0.35, 0.5], [2.2, 0.92, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const numCol = e.num?.dir === 'down' ? C.down : e.num?.dir === 'up' ? C.up : INK;
	return (
		<div style={{position: 'absolute', top: 245, left: 90, right: 90, height: 545, display: 'flex', gap: 40, opacity: a, transform: `translateY(${(1 - a) * 40}px)`, fontFamily: FONT}}>
			<div style={{flex: 1.35, background: C.panel, borderTop: `10px solid ${INK}`, borderBottom: `2px solid ${INK}`, padding: '28px 40px', position: 'relative'}}>
				<div style={{display: 'inline-block', border: `5px solid ${C.teal}`, color: C.teal, fontWeight: 900, fontSize: 44, padding: '0 18px', transform: `rotate(-4deg) scale(${stamp})`}}>{e.label}</div>
				<div style={{fontSize: 64, fontWeight: 900, color: INK, lineHeight: 1.25, marginTop: 26}}>{e.head}</div>
				<div style={{fontSize: 34, fontWeight: 500, color: C.muted, lineHeight: 1.55, marginTop: 22, display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 4, overflow: 'hidden'} as React.CSSProperties}>
					<Colored text={e.body.slice(e.head.replace('…', '').length).replace(/^[，、]/, '')} base={C.muted} />
				</div>
				{e.source && <div style={{position: 'absolute', bottom: 22, left: 40, fontSize: 26, color: C.muted, fontWeight: 700}}>{tx('source')}：{e.source}</div>}
			</div>
			<div style={{flex: 1, display: 'flex', flexDirection: 'column', gap: 24}}>
				{e.num && <div style={{background: C.panel, borderTop: `5px solid ${INK}`, padding: '20px 32px'}}>
					<div style={{fontSize: 30, fontWeight: 700, color: C.muted}}>{tx('key_number')}</div>
					<div style={{fontSize: e.num.text.length > 9 ? 72 : e.num.text.length > 6 ? 92 : 128, whiteSpace: 'nowrap', fontWeight: 900, color: numCol, lineHeight: 1.1}}>{e.num.text}</div>
				</div>}
				{e.stock && <div style={{flex: 1, background: C.panel, borderTop: `5px solid ${INK}`, padding: '16px 28px', position: 'relative'}}>
					<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
						<span style={{fontSize: 34, fontWeight: 900, color: INK}}>{e.name && e.name !== e.ticker ? `${e.name} ` : ''}{e.ticker}</span>
						<span style={{fontSize: 44, fontWeight: 900, color: e.stock.chg >= 0 ? C.up : C.down}}>{e.stock.label} {e.stock.chg >= 0 ? '+' : ''}{e.stock.chg.toFixed(2)}%</span>
					</div>
					<MiniLine series={e.stock.series} since={since} t={t} w={640} h={e.num ? 150 : 330} />
					<div style={{fontSize: 22, color: C.muted, textAlign: 'right'}}>{tx('close')} {e.stock.close.toFixed(2)}｜{tx('data_source')}</div>
				</div>}
			</div>
		</div>
	);
};

// ───────── 圖表（講稿「圖表」段給的資料點；這段不念）─────────
const TodayChartView: React.FC<{c: TodayChart; since: number; t: number}> = ({c, since, t}) => {
	const W = 1740, H = 320;
	const g = interpolate(t - since, [0, 1.2], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
	const fmt = (v: number) => `${v > 0 && c.unit === '%' ? '+' : ''}${v.toLocaleString('en-US', {maximumFractionDigits: 2})}${c.unit}`;
	const vals = c.points.map((p) => p[1]);
	const src = c.source.replace(/^https?:\/\/(www\.)?/, '').split('/')[0];
	const head = (
		<><text x={30} y={46} fill={C.txt} fontSize={30} fontWeight={700} fontFamily={FONT}>{c.title}</text>
		{src && <text x={W - 40} y={44} fill={C.muted} fontSize={22} textAnchor="end" fontFamily={FONT}>{tx('source')}：{src}</text>}</>
	);
	if (c.type === 'line') {
		let lo = Math.min(...vals), hi = Math.max(...vals); const pad = (hi - lo) * 0.15 || 1; lo -= pad; hi += pad;
		const L = 130, R = 60, T = 80, B = 50;
		const pts = vals.map((v, i) => [L + (i * (W - L - R)) / Math.max(1, vals.length - 1), T + ((hi - v) / (hi - lo)) * (H - T - B)]);
		const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ');
		const col = vals[vals.length - 1] >= vals[0] ? C.up : C.down;
		return (
			<svg width={W} height={H} style={{background: C.panel, border: `2px solid ${INK}`}}>{head}
				<path d={d} fill="none" stroke={col} strokeWidth={6} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - g} strokeLinejoin="round" />
				{pts.map((p, i) => i / Math.max(1, pts.length - 1) <= g + 0.001 && <g key={i}><circle cx={p[0]} cy={p[1]} r={8} fill={col} />
					<text x={p[0]} y={p[1] - 18} fill={C.txt} fontSize={24} textAnchor="middle" fontFamily={FONT}>{fmt(vals[i])}</text>
					<text x={p[0]} y={H - 16} fill={C.muted} fontSize={22} textAnchor="middle" fontFamily={FONT}>{c.points[i][0]}</text></g>)}
			</svg>
		);
	}
	// 橫向長條：有負值時 0 軸置中，正值往右、負值往左
	const n = c.points.length, rowH = Math.min(52, (H - 80) / n), max = Math.max(...vals.map(Math.abs)) || 1;
	const hasNeg = vals.some((v) => v < 0), x0 = hasNeg ? W / 2 + 160 : 330, span = hasNeg ? W / 2 - 400 : W - 520;
	return (
		<svg width={W} height={H} style={{background: C.panel, border: `2px solid ${INK}`}}>{head}
			{c.points.map(([label, v], i) => {
				const y = 76 + i * rowH, w = (Math.abs(v) / max) * span * g, col = hasNeg ? (v >= 0 ? C.up : C.down) : C.teal;
				const x = v >= 0 ? x0 : x0 - w;
				return <g key={i}>
					<text x={60} y={y + rowH * 0.62} fill={C.txt} fontSize={Math.min(28, rowH * 0.6)} fontWeight={700} fontFamily={FONT}>{label}</text>
					<rect x={x} y={y + rowH * 0.15} width={w} height={rowH * 0.7} rx={6} fill={col} />
					<text x={v >= 0 ? x0 + w + 14 : x0 - w - 14} y={y + rowH * 0.62} fill={col} fontSize={Math.min(28, rowH * 0.6)} fontWeight={900} textAnchor={v >= 0 ? 'start' : 'end'} fontFamily={FONT}>{fmt(v * g)}</text>
				</g>;
			})}
			{hasNeg && <line x1={x0} x2={x0} y1={66} y2={H - 14} stroke={C.muted} strokeWidth={2} />}
		</svg>
	);
};

const CountUp: React.FC<{to: number; t: number; since: number; fmt: (n: number) => string}> = ({to, t, since, fmt}) => {
	const p = interpolate(t - since, [0, 1.1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
	return <>{fmt(to * p)}</>;
};

// ───────── 各段 ─────────
// 小標（### 那一行）太長會伸到右上角的判定印章底下 → 估寬度、超過 700px 就縮字
const subSize = (t: string) => {
	const w = Array.from(t).reduce((a, ch) => a + (ch.charCodeAt(0) < 0x2e80 ? 26 : 40), 0);
	return Math.max(26, Math.min(40, Math.floor(40 * 700 / w)));
};
const Header: React.FC<{s: Section; local: number}> = ({s, local}) => {
	const a = interpolate(local, [0, 0.5], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
	return (
		<div style={{position: 'absolute', top: 120, left: 90, display: 'flex', alignItems: 'baseline', gap: 36, fontFamily: FONT, opacity: a, transform: `translateX(${(1 - a) * -60}px)`}}>
			<div style={{fontSize: 72, fontWeight: 900, color: C.txt, borderBottom: `7px solid ${C.teal}`, paddingBottom: 6}}>{s.title}</div>
			{s.sub && <div style={{fontSize: subSize(s.sub), fontWeight: 700, color: C.teal, whiteSpace: 'nowrap'}}>{s.sub}</div>}
		</div>
	);
};

const OpenScene: React.FC<{s: Section; local: number}> = ({s, local}) => {
	const text = s.lines.join('');
	return (
		<AbsoluteFill style={{padding: '250px 90px 0', fontFamily: FONT}}>
			<div style={{fontSize: 44, fontWeight: 700, color: C.teal, opacity: interpolate(local, [0, 0.4], [0, 1], {extrapolateRight: 'clamp'})}}>{tx('open_label')}</div>
			<div style={{fontSize: text.length > 60 ? 76 : 96, fontWeight: 900, lineHeight: 1.35, marginTop: 30, color: C.txt}}>
				<span style={{WebkitMaskImage: `linear-gradient(90deg, #000 ${Math.min(100, (local / 1.6) * 100)}%, transparent ${Math.min(100, (local / 1.6) * 100 + 8)}%)`}}>
					<Colored text={text} />
				</span>
			</div>
		</AbsoluteFill>
	);
};

const MarketScene: React.FC<{ep: Episode; si: number; local: number; t: number}> = ({ep, si, local, t}) => {
	const mk = ep.market!;
	const rows = mk.rows;
	const cues = ep.cues.filter((c) => c.sec === si && c.t0 <= t);
	// 最近一句提到哪個指數（名字或別名），圖就換成那個；都沒提到用主題指定的 default_chart
	const mentions = (c: Cue) => rows.findIndex((r) => [r.name, r.name.replace(/ /g, ''), ...(r.aliases ?? [])].some((n) => c.text.includes(n)));
	const secCues = ep.cues.filter((c) => c.sec === si);
	// 講稿的圖表：第一句沒提到指數的就換上；整段都在講指數，就放在最後一句
	const tcStart = ep.chart ? (secCues.find((c, i) => i > 0 && mentions(c) < 0) ?? secCues[secCues.length - 1])?.t0 : undefined;
	const showToday = tcStart !== undefined && t >= tcStart;
	const cur = [...secCues].reverse().find((c) => c.t0 <= t);
	const ev = cur ? ep.events?.[`${si}:${cur.line}`] : undefined;
	if (ev) {
		const since = secCues.find((c) => c.line === cur!.line)?.t0 ?? t;
		return <AbsoluteFill style={{fontFamily: FONT}}><EventCardView key={cur!.line} e={ev} since={since} t={t} /></AbsoluteFill>;
	}
	let pick = mk.default ?? 0, since = (secCues[0]?.t0 ?? 0) + 0.4;
	for (const c of cues) {
		const k = mentions(c);
		if (k >= 0 && k !== pick) { pick = k; since = c.t0; }
		else if (k >= 0 && k === pick && since < c.t0 && cues[0] === c) since = c.t0;
	}
	return (
		<AbsoluteFill style={{fontFamily: FONT}}>
			<div style={{position: 'absolute', top: 250, left: 90, right: 90, display: 'flex', gap: 30}}>
				{rows.map((r, i) => {
					const a = interpolate(local - i * 0.15, [0, 0.5], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.back(1.4))});
					const on = i === pick;
					const col = r.chg >= 0 ? C.up : C.down;
					return (
						<div key={i} style={{flex: 1, background: C.panel, borderTop: `5px solid ${INK}`, borderBottom: `1px solid ${INK}`, padding: '16px 26px', opacity: a, transform: `translateY(${(1 - a) * 50}px) scale(${on ? 1.03 : 1})`,
							outline: on ? `4px solid ${C.teal}` : 'none'}}>
							<div style={{fontSize: 36, fontWeight: 700, color: C.muted}}>{r.name}<span style={{fontSize: 26, marginLeft: 14, color: C.teal}}>{mk.chg_label ?? ''}</span></div>
							<div style={{fontSize: 76, fontWeight: 900, color: col, lineHeight: 1.25}}>
								<CountUp to={r.chg} t={t} since={t - local + i * 0.15} fmt={(n) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`} />
							</div>
							<div style={{fontSize: 30, fontWeight: 500, color: C.txt}}>
								<CountUp to={r.close} t={t} since={t - local + i * 0.15} fmt={(n) => n.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} />
							</div>
						</div>
					);
				})}
			</div>
			<div style={{position: 'absolute', top: 505, left: 90}}>{showToday && ep.chart ? <TodayChartView c={ep.chart} since={tcStart!} t={t} /> : <Chart row={rows[pick]} since={since} t={t} asOf={mk.as_of} />}</div>
		</AbsoluteFill>
	);
};

const PointsScene: React.FC<{ep: Episode; s: Section; si: number; t: number; chartHere: boolean}> = ({ep, s, si, t, chartHere}) => {
	const cue = [...ep.cues].reverse().find((c) => c.sec === si && c.t0 <= t);
	const cur = cue?.line ?? 0;
	const curV = verdictOf(s.lines[cur] ?? '');
	const vStart = ep.cues.find((c) => c.sec === si && c.line === cur)?.t0 ?? t;
	const secStart = ep.cues.find((c) => c.sec === si)?.t0 ?? t;
	const stampPop = interpolate(t - vStart, [0, 0.25, 0.4], [2.2, 0.92, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const first = chartHere ? cur : Math.max(0, cur - 1);   // 只留上一條＋目前這條（長段落才不會壓到字幕）；下面要放圖表時只留目前這條
	return (
		<AbsoluteFill style={{fontFamily: FONT}}>
			{curV && <div style={{position: 'absolute', top: 108, right: 90, opacity: interpolate(t - vStart, [0, 0.15], [0, 1], {extrapolateRight: 'clamp'})}}>
				<span style={{fontSize: 34, color: C.muted, fontWeight: 700, marginRight: 16}}>{tx('verdict_label')}</span><VerdictTag v={curV} big pop={stampPop} /></div>}
			<div style={{position: 'absolute', top: 260, left: 90, right: 90}}>
				{s.lines.slice(first, first + (chartHere ? 1 : 2)).map((line0, k) => {
					const v = verdictOf(line0);
					const line = v ? stripVerdict(line0) : line0;
					const li = first + k;
					const start = ep.cues.find((c) => c.sec === si && c.line === li)?.t0 ?? Infinity;
					if (t < start) return null;
					const a = interpolate(t - start, [0, 0.45], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
					const on = li === cur;
					return (
						<div key={li} style={{display: 'flex', marginBottom: 34, opacity: a * (on ? 1 : 0.55), transform: `translateX(${(1 - a) * 80}px)`,
							background: on ? C.panel : 'transparent', padding: '20px 34px', borderLeft: `8px solid ${on ? C.teal : 'transparent'}`, boxShadow: on ? '0 6px 0 #00000014' : undefined}}>
							<div style={{fontSize: (on ? 50 : 40) * (line.length > 110 ? 0.78 : line.length > 70 ? 0.88 : on && !chartHere && line.length <= 36 ? 1.36 : on && !chartHere && line.length <= 54 ? 1.18 : 1), fontWeight: on ? 700 : 500, lineHeight: 1.42, color: on ? C.txt : C.muted,
								display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: chartHere ? 3 : on ? 5 : 2, overflow: 'hidden'} as React.CSSProperties}>
								{v && <VerdictTag v={v} />}<Colored text={line} base={on ? C.txt : C.muted} />
							</div>
						</div>
					);
				})}
			</div>
			{chartHere && ep.chart && <div style={{position: 'absolute', top: 560, left: 90}}><TodayChartView c={ep.chart} since={secStart + 0.4} t={t} /></div>}
		</AbsoluteFill>
	);
};

const Body: React.FC<{ep: Episode}> = ({ep}) => {
	const fr = useCurrentFrame();
	const t = fr / FPS;
	const cue = [...ep.cues].reverse().find((c) => c.t0 <= t && t < (ep.cues[ep.cues.indexOf(c) + 1]?.t0 ?? c.t1 + 0.6));
	const si = cue?.sec ?? 0;
	const s = ep.sections[si];
	const secStart = ep.cues.find((c) => c.sec === si)?.t0 ?? 0;
	const local = t - secStart;
	const fade = interpolate(local, [0, 0.35], [0, 1], {extrapolateRight: 'clamp'});
	// 沒有市場段的主題：講稿的圖表放在開場後的第一個一般段落
	const hasMarketSec = !!ep.market && ep.sections.some((x) => x.kind === 'market');
	const chartSec = ep.chart && !hasMarketSec ? ep.sections.findIndex((x) => x.kind === 'points') : -1;
	return (
		<AbsoluteFill>
			<TopBar ep={ep} t={t} />
			<AbsoluteFill key={si} style={{opacity: fade}}>
				{s.kind !== 'open' && <Header s={s} local={local} />}
				{s.kind === 'open' && <OpenScene s={s} local={local} />}
				{s.kind === 'market' && ep.market && <MarketScene ep={ep} si={si} local={local} t={t} />}
				{(s.kind === 'points' || (s.kind === 'market' && !ep.market)) && <PointsScene ep={ep} s={s} si={si} t={t} chartHere={si === chartSec} />}
			</AbsoluteFill>
			{ep.burn_subs && <Subtitle cue={cue} t={t} bottom={ep.market ? 96 : 40} />}   {/* 預設不燒字幕：用 captions.srt 當 YouTube CC */}
		</AbsoluteFill>
	);
};

export const Daily: React.FC<{ep: Episode}> = ({ep}) => {
	applyTheme(ep);
	const intro = f(ep.intro), body = f(ep.narration + 0.6);
	return (
		<AbsoluteFill style={{background: C.bg}}>
			<Backdrop />
			<Sequence durationInFrames={intro}><Intro ep={ep} /></Sequence>
			<Sequence from={intro} durationInFrames={body}><Body ep={ep} /></Sequence>
			<Sequence from={intro + body}><Outro ep={ep} /></Sequence>
			{ep.market && <Sequence from={intro} durationInFrames={body}><Ticker rows={ep.market.rows} /></Sequence>}
			<Sequence from={intro}><Audio src={staticFile(ep.vo)} /></Sequence>
			{ep.jingle && <Sequence durationInFrames={intro}><Audio src={staticFile(ep.jingle.intro)} /></Sequence>}
			{ep.jingle && <Sequence from={intro + body}><Audio src={staticFile(ep.jingle.outro)} /></Sequence>}
		</AbsoluteFill>
	);
};
