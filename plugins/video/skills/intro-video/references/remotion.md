# Remotion で編集して書き出す

Remotion は個人と小さな会社（3 人まで）は無料で、それ以外は有料のライセンスが要る。パートタイムや業務委託の人、同じコードを使う取引先の人も数える場合があるので、[規約](https://www.remotion.dev/docs/terms)で確かめてもらう。最初にユーザーに伝える。

## プロジェクト

作業ディレクトリ（例: `video/`）に、対象リポジトリのワークスペースから独立させて作る（Remotion は Chrome を抱えて重い）。

```
video/
├── prepare.mjs        素材の前処理（下記）
├── scripts.md, scripts.vo.srt, scripts.<言語>.srt
├── public/            demo.mp4, slides/, vo.mp3, bgm.mp3, norm/
└── src/               Root.tsx, Video.tsx, theme.ts（fps、色、フォント、sec()）, components.tsx, scenes/, generated/
```

`package.json` の scripts は `assets`（`node prepare.mjs`）、`studio`、`render`（`out/final.mp4`）、`render:clean`（字幕なし版）にし、どれも先に `assets` を流す。

## prepare.mjs

- 字幕用の SRT を読み、`src/generated/subtitles.json` に書く（CRLF や末尾の空行のゆれを吸収する）。書き出すたびに読み直すので、字幕の文言をシーンのコードに書き写さない。
- 字幕用と読み上げ用の SRT のキュー数や時刻が食い違ったら止める。
- 書き出しに使った SRT を `out/` に控える。控えるのは `render` の成功後だけにする（`studio` や失敗した書き出しで上書きすると、前回との違いが分からなくなる）。
- `public/` にある素材だけを `src/generated/assets.json` に書き、ない素材はシーン側でプレースホルダーを出す。
- VO と BGM を `loudnorm` で -15 LUFS にそろえて `public/norm/` に書く。作り直すかは元ファイルのハッシュで決める（更新日時では、古い日時のまま差し替えた VO を見落とす）。
- インストール済みのフォントを探して `src/generated/font.json` に書く（下記）。

## 共通部品の注意

- `useFade(from, to, inDur, outDur)`: `interpolate` の入力は厳密に増加していないとエラーになる。区間よりフェードが長くても逆転しないよう、中間の 2 点を次のように取る。

  ```ts
  const b = Math.max(from + 1, Math.min(from + inDur, to - 2));
  const c = Math.min(to - 1, Math.max(to - outDur, b + 1));
  // interpolate(frame, [from, b, c, to], [0, 1, 1, 0])
  ```
- `Sequence` の中の `useCurrentFrame()` は区間の頭から数える。キューの時刻（動画全体の秒数）で演出を書くなら、`Sequence` で包まず、フレームで区間を判定してから描く。包むと開始時刻ぶん遅れる。
- 素材の動画は `OffthreadVideo` で `muted` にし、音は `Audio` で別に鳴らす。

## 手持ち素材を切り出す

使う区間を推測で決めない。シーン検出（`select='gt(scene,0.3)',showinfo`）とコンタクトシート（`fps=4,scale=480:-1,tile=6x4`）で、ウィンドウが現れる瞬間などを特定する。実測の主張（起動時間など）に絡むカットは、どの時刻を起点にしたかを報告に書く。Windows の ffmpeg は `drawtext` が落ちることがあるので、文字は Remotion で描く。

## 字幕とフォント

- 白い文字に黒い縁取り（`WebkitTextStroke` と `paintOrder: "stroke fill"`）と薄い影、大きさは帯に 2 行が収まる 52〜56px（`references/source-slides.md`）。
- 字幕と Remotion で描く文字は素材の書体にそろえる。スライドなら PDF の埋め込みフォント（pymupdf の `page.get_fonts()`、`ABCDEF+` の後ろ）。Marp の PDF は本文が Type3 で名前が取れないので、テーマの CSS の `font-family` から取る。
- **インストール済みのフォントを優先する**。`@remotion/google-fonts` は日本語を細かいファイルで配信していて、Noto Sans JP の 2 ウェイトで 248 回の取得になり、描画前の待ち（30 秒）を超えて止まった。`prepare.mjs` で `process.platform` ごとにフォントのフォルダを探し（Windows は `%LOCALAPPDATA%\Microsoft\Windows\Fonts` と `%WINDIR%\Fonts`、macOS は `~/Library/Fonts` など、Linux は `fc-list : family file`）、あれば `fontFamily: '"<フォント名>", sans-serif'` と名前で指定する。
- なければ `loadFont` に、そのフォントが持つ subset（日本語なら `["japanese", "latin"]`）を付ける。それでも止まるなら `--timeout=180000`。

## 音声

- VO は 0 フレーム目から置く。BGM は `volume` を関数にして頭と尻をフェードし、音量の定数を `Video.tsx` の上に dB のコメント付きでまとめる。

## 書き出し

- 1920×1080、30 fps。`npm run render` をバックグラウンドで実行する。
- 速さを決めたのは並列数ではなく描画前の待ちだった（4 分 24 秒、7,932 フレーム、Core Ultra 5 125H）: Google Fonts で約 10 分、インストール済みのフォントで約 3 分 20 秒。`--concurrency` や `--gl=angle` は差がなかった。遅ければ、まず外から取ってくるもの（Web フォント、URL の画像）を手元に置く。
- TSX はヒアドキュメントではなくファイル書き込みのツールで書く（`$` やテンプレートリテラルがシェルに解釈される）。
