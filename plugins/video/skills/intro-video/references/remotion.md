# Remotion で編集して書き出す

[Remotion](https://www.remotion.dev/) は React で動画を組むツール。シーンをコードで描けるので、台本の時刻をそのまま数値で書け、字幕や素材を差し替えて何度でも書き出し直せる。

Remotion は個人と小さな会社（3 人まで）は無料で、それ以外は有料のライセンスが要る。人数には、パートタイムや業務委託の人、同じ Remotion のコードを使う取引先の人も数える場合があるので、[規約](https://www.remotion.dev/docs/terms)で確かめてもらう。最初にユーザーに伝える。

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
- 書き出しに使った SRT を `out/` に控えておく。次に直されたとき、どのキューが変わったかを中身で比べるため。控えるのは書き出しが成功したあとにする（`render` のスクリプトで `remotion render` の後ろに置き、`studio` では控えない）。Studio を開いただけや、失敗した書き出しで控えを上書きすると、前回との違いが分からなくなる。
- 収録のテイク（`out/demo.mp4`）が新しければ `public/` にコピーする。
- `public/` にある素材を見て、あるものだけを `src/generated/assets.json` に書く。ない素材はシーン側でプレースホルダー（点線の枠に「ここに◯◯」）を出す。素材がそろう前から通しで見られるようにするため。
- VO と BGM を `loudnorm` で -16 LUFS にそろえ、`public/norm/` に WAV で書く（`references/audio.md`）。作り直すかは元ファイルの中身で決める（ハッシュを `public/norm/` に控えて比べる）。更新日時で決めると、古い日時のまま差し替えた VO を見落とす。

## 共通部品

- `sec(s)`: 秒をフレーム数にする。シーンの時刻はすべて秒で書き、`sec()` で変換する。
- `useFade(from, to, inDur, outDur)`: 区間の頭でフェードイン、尻でフェードアウトする不透明度。`interpolate` の入力は厳密に増加していないとエラーになるので、フェードの長さが区間より長くても点が逆転しないよう、中間の 2 点を次のように取る。

  ```ts
  const b = Math.max(from + 1, Math.min(from + inDur, to - 2));
  const c = Math.min(to - 1, Math.max(to - outDur, b + 1));
  // interpolate(frame, [from, b, c, to], [0, 1, 1, 0])
  ```
- **`Sequence` の中の `useCurrentFrame()` は、その区間の頭から数えたフレームを返す**。動画全体の秒数（キューの時刻など）で演出を書くなら、`Sequence` で包まずに、`useCurrentFrame()` の値で表示する区間かどうかを判定してから描く。包んだうえで全体の秒数と比べると、演出が区間の開始時刻ぶん遅れる。
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
- 字幕と、Remotion で描く文字（締めのカードなど）の書体は、素材の書体にそろえる。スライドなら PDF の埋め込みフォントを見る（pymupdf の `page.get_fonts()`。`ABCDEF+NotoSansJP-Regular` のような名前の `+` の後ろ）。
- フォントはこの PC にインストールされたものを優先する。`prepare.mjs` でフォントファイルの有無を調べ、結果を `src/generated/font.json` に書く。調べる場所は `process.platform` で分ける。
  - Windows（`win32`）: ユーザーごとの `%LOCALAPPDATA%\Microsoft\Windows\Fonts` と `%WINDIR%\Fonts`
  - macOS（`darwin`）: `~/Library/Fonts`、`/Library/Fonts`、`/System/Library/Fonts`
  - Linux: `fc-list : family file` があればそれで探す。なければ `~/.local/share/fonts`、`~/.fonts`、`/usr/share/fonts`、`/usr/local/share/fonts` をサブフォルダまで探す（`/usr/share/fonts/opentype/noto/` のように深い所に入る）
  - あれば `fontFamily: '"<フォント名>", sans-serif'` と名前で指定するだけで、ヘッドレス Chrome がシステムから読む。可変フォント（`<名前>[wght].ttf`）なら、1 ファイルで太さを変えられる。
  - 理由: `@remotion/google-fonts` は日本語を文字の範囲ごとの細かいファイルで配信していて、Noto Sans JP の 2 ウェイトで 248 回の取得になった。回線が遅いと、描画前の待ち（30 秒）を超えて書き出しが止まる。
  - インストールされていなければ、`@remotion/google-fonts/<フォント>` の `loadFont` に、そのフォントが持っている subset を付けて読む（日本語のフォントなら `["japanese", "latin"]`。持っていない subset を指定するとエラーになる）。それでも止まるなら `--timeout=180000`。
- 字幕なし版（CC を別に出す用）の Composition も作る。props で字幕の有無を切り替える。

## 音声

- VO: `<Audio src={staticFile(assets.voTrack)} />` を 0 フレーム目から置く。
- BGM: `Sequence from={sec(BGM_START)}` の中に置き、`volume` を関数にして、頭のフェードイン、一定の音量、尻のフェードアウトを `interpolate` で書く。音量の定数は `Video.tsx` の上にまとめ、dB でコメントを付ける。ユーザーが自分で調整できるように。

## 書き出し

- 1920×1080、30 fps を基本にする。収録素材は 60 fps でもよい（`OffthreadVideo` が間引く）。
- `npm run render` で書き出す。バックグラウンドで実行して終わりを待つ。
- 速さを決めるのは、並列数より描画前の待ちだった。スライドの動画（4 分 24 秒、7,932 フレーム、Core Ultra 5 125H）の実測:
  - Google Fonts で Noto Sans JP を読んでいたときは約 10 分。各タブがフォントを取りに行くため。
  - インストール済みのフォントに替えたら約 3 分 20 秒（約 40 fps）。
  - 900 フレームで `--concurrency` を 6 / 9 / 13 / 18 と変えても、22〜24 秒で差がなかった。既定のままでよい。
  - `--gl=angle`（GPU で描画）にも差はなかった。同梱の ffmpeg は NVENC しか持たず、Intel Arc ではエンコードを GPU に任せられない。
- 遅いと感じたら、まず外から取ってくるもの（Web フォント、URL の画像）を手元に置き換える。
- TSX を書くときは、シェルのヒアドキュメントではなくファイル書き込みのツールを使う。テンプレートリテラルや `$` がシェルに解釈されて壊れるため。
