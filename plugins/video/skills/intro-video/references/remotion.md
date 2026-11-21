# Remotion で編集して書き出す

[Remotion](https://www.remotion.dev/) は React で動画を組むツール。シーンをコードで描けるので、台本の時刻をそのまま数値で書け、字幕や素材を差し替えて何度でも書き出し直せる。

Remotion は個人と従業員 3 人以下の会社は無料、それ以外は有料のライセンスが要る。最初にユーザーに伝える。

## プロジェクトの構成

作業ディレクトリ（例: `video/`）に作る。対象リポジトリの pnpm / npm ワークスペースには入れず、`npm install` で独立させる。Remotion はレンダリング用の Chrome などを抱えて重いので、ワークスペースに入れると本体の依存のインストールが遅くなる。

```
video/
├── package.json        scripts: assets, studio, render, render:clean
├── prepare.mjs         素材の前処理（下記）
├── scripts.md          台本
├── scripts.vo.srt      読み上げ用の原稿
├── scripts.<言語>.srt  字幕
├── record-demo.mjs     収録スクリプト（アプリの場合）
├── public/             素材。staticFile() で参照する
│   ├── demo.mp4        収録したテイク
│   ├── <手持ち素材>.mp4
│   ├── slides/         スライドの画像（スライドの場合）
│   ├── vo.mp3, bgm.mp3
│   ├── fonts/          ローカルのフォント
│   └── norm/           音量をそろえた音声（prepare.mjs が作る）
└── src/
    ├── index.ts        registerRoot
    ├── Root.tsx        Composition の定義
    ├── Video.tsx       タイムライン（シーンの並び、字幕、音声）
    ├── theme.ts        fps、尺、色、フォント、sec()
    ├── components.tsx  共通部品（Footage、useFade など）
    ├── scenes/         コードで描くシーン
    └── generated/      prepare.mjs の出力（subtitles.json、assets.json）
```

`package.json` の scripts の例:

```json
{
  "assets": "node prepare.mjs",
  "studio": "npm run assets && remotion studio src/index.ts",
  "render": "npm run assets && remotion render src/index.ts Main out/final.mp4",
  "render:clean": "npm run assets && remotion render src/index.ts MainClean out/final-nosubs.mp4"
}
```

## prepare.mjs の役割

レンダリングの前に毎回走らせ、Remotion が読む JSON を作る。

- 字幕用の SRT（CC 用にもう一つあればそれも）を読み、キューごとに `{ index, start, end, ja, en }` のような形で `src/generated/subtitles.json` に書く。SRT の行末（CRLF）や末尾の空行など、ユーザーがエディタで直したときに混ざるゆれを吸収する。
- 書き出しのたびに SRT を読み直すので、ユーザーが SRT を直したら `npm run render` だけで字幕が変わる。字幕の文言をシーンのコードに書き写さない。
- 字幕用と読み上げ用の SRT のキュー数や時刻が食い違っていたら、警告を出して止める。気づかないまま書き出すと、字幕と VO がずれた動画ができる。
- 書き出しに使った SRT を `out/` に控えておく。次に直されたとき、どのキューが変わったかを比べるため。
- 収録のテイク（`out/demo.mp4`）が新しければ `public/` にコピーする。
- `public/` にある素材を見て、あるものだけを `src/generated/assets.json` に書く。ない素材はシーン側でプレースホルダー（点線の枠に「ここに◯◯」）を出す。素材がそろう前から通しで見られるようにするため。
- VO と BGM を `loudnorm` で -16 LUFS にそろえ、`public/norm/` に WAV で書く（`references/audio.md`）。元ファイルより新しければ作り直さない。

## 共通部品

- `sec(s)`: 秒をフレーム数にする。シーンの時刻はすべて秒で書き、`sec()` で変換する。
- `useFade(from, to, inDur, outDur)`: 区間の頭でフェードイン、尻でフェードアウトする不透明度。`interpolate` の入力は厳密に増加していないとエラーになるので、フェードの長さが区間より長くても点が逆転しないよう、中間の 2 点を `max(a+1, …)` と `min(d-1, …)` で挟む。
- `Footage({ file, from, cropTop })`: `OffthreadVideo` で素材を映す。`from` で素材の頭を飛ばし（`startFrom={sec(from)}`）、`cropTop` でウィンドウのタイトルバーなどを上から切る（絶対配置で上にずらし、幅を 100% にする）。素材は必ず `muted` にし、音は `Audio` で別に鳴らす。

## 素材を切り出す

手持ち素材は長さが適当なことが多い。どこから使うかを推測で決めず、確かめてから決める。

- ffmpeg のシーン検出（`select='gt(scene,0.3)',showinfo`）で、画面が大きく変わる時刻を出す。
- 0.25〜0.5 秒ごとのフレームを並べたコンタクトシートを作って見る（`fps=4,scale=480:-1,tile=6x4`）。ウィンドウが現れる、画面が描画される、といった瞬間を特定する。
- 実測の主張（起動時間など）に絡むカットは、映像の時刻で確かめる。ストップウォッチなどを重ねるなら、どの時刻を起点にしたかを報告に書く。
- Windows の ffmpeg では `drawtext` が fontconfig の都合で落ちることがある。文字を焼き込む処理は ffmpeg ではなく Remotion でやる。

## 字幕を焼き込む

- `subtitles.json` から現在の時刻のキューを探し、画面下に出す。
- 白い文字に黒い縁取り（`WebkitTextStroke` と `paintOrder: "stroke fill"`）と薄い影。1920×1080 なら 56〜64px、下の余白 64px 程度。
- ローカルのフォントは `public/fonts/` に置き、`@remotion/fonts` の `loadFont({ family, url: staticFile("fonts/…") })` で読む。Google Fonts は `@remotion/google-fonts` で読む。指定したフォントが読めないときに備えて、Noto Sans JP などを後ろに並べる。
- 字幕なし版（CC を別に出す用）の Composition も作る。props で字幕の有無を切り替える。

## 音声

- VO: `<Audio src={staticFile(assets.voTrack)} />` を 0 フレーム目から置く。
- BGM: `Sequence from={sec(BGM_START)}` の中に置き、`volume` を関数にして、頭のフェードイン、一定の音量、尻のフェードアウトを `interpolate` で書く。音量の定数は `Video.tsx` の上にまとめ、dB でコメントを付ける。ユーザーが自分で調整できるように。

## 書き出し

- 1920×1080、30 fps を基本にする。収録素材は 60 fps でもよい（`OffthreadVideo` が間引く）。
- `npm run render` で書き出す。2 分の動画で 5〜10 分かかるので、バックグラウンドで実行して終わりを待つ。
- TSX を書くときは、シェルのヒアドキュメントではなくファイル書き込みのツールを使う。テンプレートリテラルや `$` がシェルに解釈されて壊れるため。
- ユーザーが台本を直したと言ったら、どのファイルが変わったか（更新日時）を確かめてから書き出し直し、変わったファイルを報告する。
