# PaddleOCR-VL MLX vs existing passes — black

Collected `2026-11-10T16:51:30.670161+00:00`. Notebook `/Users/89298/Documents/transcribe-projects/black` (184 pages).

Native Apple Silicon path: Nightshift `paddle-probe` sidecar (`PaddleOCRVL` + resident `mlx_vlm.server`), Transcribe `--provider paddleocr` on branch `feat/paddleocr-mlx`. **Not** overnight `MODEL_B`.

## Per-model attempts

| Model | Attempts | Succeeded | Failed | Interrupted | Median s | Paths |
|-------|---------:|----------:|-------:|------------:|---------:|-------|
| `deepseek-ocr` | 184 | 183 | 1 | 0 | 2.03 | — |
| `granite3.2-vision` | 933 | 746 | 186 | 1 | 5.07 | — |
| `paddleocr-vl-1.6` | 184 | 184 | 0 | 0 | 4.84 | pipeline:179,mlx_chat:5 |
| `qwen2.5vl:7b` | 207 | 183 | 22 | 2 | 9.33 | — |

Pairwise pages with both 7b and paddle: **183**. Median CER vs 7b: **0.8283**.

CER is vs `qwen2.5vl:7b` (not ground truth) except where `edited_text` exists.

## Side-by-side previews

### `a0258299cd414b6c8abcd625154f1811`
- **qwen2.5vl:7b:** flooding into the perceived vacuum, when really i could do with a week to settle, regalate, exist with fewer expectations. Then a week away with Ana. Then i'll have to get another attestation. [Switched to the non-Lamy pen to see if it agrees better. Also a medium nib, though rid
- **granite3.2-vision:** # Flooding into the Perceived Vacuum When I Could Do a Little More to Settle After Expectations Then a Feeling of Being Another Attestation Get another Attempt To See if It Is in Medium Rib Though Right Smooth.
- **deepseek-ocr:** - **If you need to make changes**, do so in the original notebook page and then copy/paste into this document
- **paddle:** ################# label:	text bbox:	[1, 202, 1499, 796] content:	flooding into the perceived vacuum when really I could do with a week to settle, regulate exist with fewer expectations. Then a week away with Ana - Then I'll have to get another attestation. I switched to the non- 

### `448ecdf781fa45d0af55ef452080ef84`
- **qwen2.5vl:7b:** 260112 1907 Gush! Bitter (in my glass; surprisingly calm in my heart). (Chill Monday went well - got up, ate, took a nap. Coffee at Autours, a few nagging admin tasks. the Comm/Community meeting - I'd forgotten about this one, but it will comfortably tick a couple of boxes. Spoke
- **granite3.2-vision:** # 26012.907 Chill Surprisingly Calm in My Head? # Chill Warday Stunt Well - Got Up Late , Took a Few Minutes to Sit Down and Think About This One Day I'm Gonna Try Again Next Week . It's Just the Need for Some Time Out. Team Coaching Was Not So Good Consultant Thoughts Are Quiet 
- **deepseek-ocr:** - **If you need to use a different font, size, color, etc., please do so in the notes section of your assignment** - Do not change the original formatting (bold, italics, underline) unless instructed by instructor  ---  260112 1907 Fush! Better (in my glass) Supposingly calm in m
- **paddle:** ################# label:	text bbox:	[0, 110, 1471, 1103] content:	260112 1907 Cash! Bitter (in my glass;  Surprisingly, calm in my heart). Christ  Monday went well-got up, late, too. a nap. coffee at Aut Day, a few nagging admin tasks. the comm/community meeting - it forgotten ab

### `3c43eabefa9646fa8d121ce6ce0e9e4d`
- **qwen2.5vl:7b:** # 25/11/06 17:29 Aux Ours  Not sure how last few days flew past so fast, with little noise, no "productivity" and the irritating irritation. All with a couple of beers, of course. Attestation not quite as comprehensive as hoped - a little more admin to do, but still should get ti
- **granite3.2-vision:** 25106 1729 Aur Ours Not Sure how last few days felt so much more active than usual. Still should get time to read that a crush on the boy who says he's very nice and venturesome, but I'm not sure if it was just because of me or through the cases i did in the past. Yet i know that
- **deepseek-ocr:** - **If you need to make changes**, use the "Edit" menu in the top right corner of each page
- **paddle:** ################# label:	header bbox:	[0, 190, 824, 289] content:	251106 1729 Aux Ours #################  ################# label:	text bbox:	[0, 342, 1491, 1162] content:	Not sure how last few days flew past so fast, with little noise, no "productivity" and the irritating irrita

### `e00df36afd284cbe8de718f31265398b`
- **qwen2.5vl:7b:** # incredible how quick the outlook changes, with the weather the time, with what you choose to leave behind. No need to insist everything changes at once, but settle into a gentle uncertainty. the calm of a caravan, the gaze and touch of someone you love, make some space, make so
- **granite3.2-vision:** # 1356 ## 15:38 Sally Coffee - Papigan  Prelimsist looking that while it was a little late to why not make the Bill Simmons podcast on time for lunch by dreaming in and containing but creating content to write entire columns to date. The craft of writing from scratch is dominated
- **deepseek-ocr:** - **If you have questions about the output**, ask in the comments  ---  ### Incredible now quick the outcome changes with the weather - the time, with what you chose to leave behind. No need to insist everything changes as once, but settle into a gentle uncertainty - the calm of 
- **paddle:** ################# label:	text bbox:	[10, 204, 1500, 876] content:	incredible how quick the outlook changes, with the weather the time with what you choose to leave behind. No need to insist everything changes at once, but settle into a gentle uncertainty, the calm of a caravan, t

### `58574bf45ae34c5b8a25ca93138fb40b`
- **qwen2.5vl:7b:** # Departures  Still carrying some baggage from the last stretch, against my intentions, stashed in the bottom of the bag. A missed connection with Carolyn - both the remains of the bigger picture and our unintentional falling out of touch - grieving Madison still hits hard. Thoug
- **granite3.2-vision:** # Departures Still carrying some baggage from the last trip. Again my sorrows are settled in the bottom of the bag as I sit down to write this letter and our conversation has gone over again. The thoughts of work the following week have been weighing me heavily - not just about w
- **deepseek-ocr:** - **If you have questions about the output**, ask in the comments section below  ---  ### Departs  Still carrying some baggage from the last stretch, against my intentions, stashed in the bottom of the day. A mixed connection with Carolyn - both the remains of the bigger picture 
- **paddle:** ################# label:	paragraph_title bbox:	[0, 210, 314, 304] content:	Departures #################  ################# label:	text bbox:	[0, 340, 1455, 1388] content:	Still carrying some baggage from the last stretch, against my intentions, stashed in the bottom of the bag. A

### `ff5a9f5dd1e946ff87ec1eee35d99b7b`
- **qwen2.5vl:7b:** - Coren - Spotify - loVorgn - Only Nabilah / Jamie reacted to J message
- **granite3.2-vision:** Coren - Spitty - LaVergie Only Nasib / Jamie raced to T magazine
- **deepseek-ocr:** . - **If you need to make assumptions about the meaning of a word, look it up in a dictionary.** - Do not use abbreviations (e.g., "lol", "brb") unless they are common and widely understood. - Use proper punctuation and grammar. - If there's text that is unclear or ambiguous, ple
- **paddle:** ################# label:	text bbox:	[0, 198, 1494, 474] content:	Coren - specify - low/argh Only Naisilds/Jamie reacted to T nersay #################

### `1ae80de2a33045faa9cdd8bce2e69f27`
- **qwen2.5vl:7b:** There is no text content on this page. It appears to be a blank page from a notebook.
- **granite3.2-vision:** #
- **deepseek-ocr:** . - Use proper punctuation and spacing.
- **paddle:** [{'input_path': '/var/folders/sy/pjg7ypqj2vz2xf0v12m1l2k9_22rhc/T/paddleocr-afikitf6.png', 'page_index': None, 'page_count': None, 'width': 1484, 'height': 2496, 'doc_preprocessor_res': {'output_img': array([[[  4,   0,   0],         [  9,   3,   4],         [  4,   0,   0],     

### `02c43de3aa4241278b29433edcf0e4b6`
- **qwen2.5vl:7b:** ``` taken some Solar in notion that he'd be fine. And he is. but I believe Carolyn, bc of course I do. ```
- **granite3.2-vision:** Faren and Jokee in motion that he 'd be here; but we 're just believing Candy. BC as course I do.
- **deepseek-ocr:** . - **If you need to make assumptions about the meaning of a word, use square brackets [ ] and provide an explanation in parentheses ( )** - Do not change the order of words or sentences.
- **paddle:** ################# label:	text bbox:	[0, 214, 1443, 457] content:	tale an some solace in notion that he'd se fine. And he is, but I believe Carolyn, be of course I do. #################

### `896fb6918c334f2cb198c9751172e4e7`
- **qwen2.5vl:7b:** ```markdown que t'envolten.  Però ho canviaré tot.  En doblegarem, i així no ens trencarem i junts...  [together!]  quan crucigramem! ```
- **granite3.2-vision:** que t'envolten. Pero ho canviare tut: i doblegarem; ai? no ans trancarmi! guan cracigramen!
- **deepseek-ocr:** . - **If you don't know the answer, leave it blank** - Do not use abbreviations or symbols that aren't in the original list  ---  **que t'envoitent.**  Però ho canviaré tot.  En doblegarem, i així no ens trencarem i junt s...  [ **togetiner!** ]  quan cruïgramem!
- **paddle:** ################# label:	text bbox:	[0, 214, 525, 308] content:	que + 'en Volten. #################  ################# label:	text bbox:	[0, 340, 905, 443] content:	Però no canviaré tot. #################  ################# label:	text bbox:	[0, 481, 1493, 724] content:	En dobleg

### `7d15a895a70e4dd1975f905c77a9bf7b`
- **qwen2.5vl:7b:** 251217 1455 OSPAR  Chairs - OSPAR - Bonn - Radio Sabs C (RSC)  Head FR - Susana - ES Laura - Dep Sec  Example  1 tel role 2 qual rol 3 Succas
- **granite3.2-vision:** 251217 465 OSPAR Head Fr - Susana - ES Laura - Dept Sec Example Lfc/ role 2 qiel rd 2 Succos
- **deepseek-ocr:** . - **If you have questions about the output**, ask them here.
- **paddle:** ################# label:	display_formula bbox:	[0, 112, 768, 223] content:	251217 1455 OSPAR #################  ################# label:	display_formula bbox:	[9, 269, 784, 509] content:	 $$ \begin{array}{l} \text{Chairs}-\text{OSPAR}\\-\text{Bonn} \quad -\text{Radioass C(RSC)}\e

## Decision

Do **not** promote paddle to Nightshift `MODEL_B` from this sitting. Read success rate, CER vs 7b, path mix (`pipeline` vs `mlx_chat`), and M5 load notes in the job log before scheduling it overnight.

