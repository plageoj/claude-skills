# VO と音量

VO は、動画の 0:00 から並んだ 1 本のファイル（`public/vo.mp3`）にそろえる。

## srt-dubbing で合成する

[plageoj/srt-dubbing](https://github.com/plageoj/srt-dubbing) は、SRT の各キューを Edge TTS で読み、キューの開始時刻に並べる。Python 3.10 以上、ffmpeg、uv が要る（uv がなければ `pip install .` で入れ、`uv run X` を `python X` / `X` に読み替える）。

作業ディレクトリの中に clone し、作業ディレクトリから実行する。

```bash
git clone https://github.com/plageoj/srt-dubbing
uv run --project srt-dubbing srt-dubbing/viet_dubbing.py --srt scripts.vo.srt --voice ja-JP-KeitaNeural --rate +15% --audio-only
```

- `--voice` は edge-tts の音声 ID（`uv run edge-tts --list-voices`）。`female` / `male` はベトナム語の音声の別名なので使わない。候補を 2〜3 個合成して選んでもらう。
- `--rate`: ja-JP-KeitaNeural は既定だと遅く聞こえ、`+15%` でちょうどよいと言われた。遅くするなら `--rate=-10%`。
- 英字・数字・同音の語を含むキューを先に数個合成して聞き、読みを直してから全体を合成する。エージェントは音を聞けないので、聞いてほしいキューの番号と文を並べてユーザーに頼む（確認を挟まないときは報告に載せる）。
- キャッシュと MP3 は実行したディレクトリにでき、MP3 は `<SRT 名>_audio_<日時>.mp3` として実行のたびに増える（`--audio-only` では `--out` が効かない）。いちばん新しいものを `public/vo.mp3` にコピーする。
- **失敗したキューがあっても MP3 は出る**（そのキューは無音）。終わりの表の `Failed` が 0 でなければ、`retry_failed_tts.py` に同じ `--srt` `--voice` `--rate` を渡して作り直し、合成し直す。
- **キャッシュ**は実行したディレクトリの `tts_<SRT 名>/`（`--rate` を付けると `tts_<SRT 名>_rate+15/`）に `cue_<4 桁>.mp3` で残る。キーは SRT のファイル名・速さ・キュー番号だけなので、声を変えたとき、別の作品で同じ名前の SRT を使うときはフォルダを消す。
- Edge TTS は音声の末尾に約 0.9 秒、頭に約 0.2 秒の無音を付ける。srt-dubbing は末尾だけ削って長さを測る。キューより長い音声は速められる（最大 2 倍）。

### 時刻を音声の長さから組む

1. 仮の時刻（各キューを 1 秒 4 字程度で割った長さ）で `scripts.vo.srt` を作り、合成する。
2. キャッシュの `cue_*.mp3` の長さを、末尾の無音を除いて測る（ffprobe の長さだと、間がすべて約 0.9 秒延びる）。`silencedetect=n=-50dB:d=0.1` の最後の `silence_start`＋0.05 秒を長さにする。
3. SKILL.md の工程 3 の表で時刻を組み直し、字幕用の SRT にも同じ時刻を入れる。TTS がキューの中で置く間は、ja-JP-KeitaNeural で読点約 0.4 秒、句点約 1 秒だった。声を変えたら測り直す。
4. 組み直した SRT で再実行する（キャッシュで並べ直すだけ）。

この手順は `build_srt.py` などに組み込んでおく。

### 原稿を直したあと

キャッシュはキュー番号で引かれ、文言が変わっても使い回される。

- 文言を直したキュー: `cue_<番号>.mp3` と `cue_<番号>.mp3.fast` を消す。合成の前に、そのキューの時刻を仮の長さに広げておく。前の短い枠のまま合成すると、枠の 2 倍を超えた音声が速め（`--rate`＋25%）で作り直されてキャッシュに残り、そのキューだけ早口になる。作り直したら時刻を組み直す。
- 時刻だけ: キャッシュはそのままでよい。
- キューの追加・削除: フォルダごと消して全体を作り直す。

## 録音を受け取る

- 発話の区間（`silencedetect`）を各キューの開始時刻と比べる。大きくずれていれば、キューの時刻を録音に合わせるか、録音を切って並べ直すかを訊く。
- 間を足すなら録音を切って無音を挟み、文言を変えるならそのキューを録り直してもらう。そのあと時刻を取り直す。

## 音量をそろえる

VO と BGM を `loudnorm` で -15 LUFS にそろえておくと、Remotion の音量を「VO より何 dB 下げるか」で書ける。

```bash
ffmpeg -y -i public/vo.mp3 -map 0:a -af loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json -f null -
ffmpeg -y -i public/vo.mp3 -map 0:a -af loudnorm=I=-15:TP=-1.5:LRA=11:measured_I=…:measured_TP=…:measured_LRA=…:measured_thresh=…:offset=…:linear=true -ar 48000 public/norm/vo.wav
```

1 回目で測った値を 2 回目に渡す。1 回だけの loudnorm では、書き出したものが -16.5 LUFS になり目安を外れた。2 回でも、AAC に書き出すと 0.3 LU ほど下がる。目標を目安（-14〜-16）の真ん中にするのはそのため。

- BGM は VO より 15 dB 下（音量 0.178）から始め、声が埋もれるなら 18 dB 下（0.126）まで。VO の少し前から 1.5 秒かけて入れ、最後の数秒でフェードアウト。
- ダッキングはユーザーが望んだときだけ。
- 書き出したら `ebur128=peak=true` で全体のラウドネスとピークを測って報告する。
