# BOUNCE BACK — two-card playable demo

This local web game uses your **actual photographs**, cropped to the printed playing cards, for **J♥ (hearts_J)** and **A♣ (clubs_A)**.

## Launch (Mac / Windows / Linux)

1. Install Python 3.10 or newer.
2. Unzip this folder and open a terminal **inside** `bounce-back-demo`.
3. Run:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python -m uvicorn server:app --reload
   ```

   Windows PowerShell: activate with `.venv\Scripts\Activate.ps1` and use `python` instead of `python3` if necessary. If activation is blocked, use `.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.venv\Scripts\python.exe -m uvicorn server:app --reload`.

4. Open **http://localhost:8000** in Chrome (or another current browser).
5. Allow camera access. **Click LIVE SCAN A CARD**. Align the entire card with the **yellow 5:7 rectangular guide** in the Mac webcam preview, hold steady for two detections, and the card fills the next slot automatically. Repeat with the other physical card (either order). Manual Test Mode remains available.
6. Press **Start Battle**. Player 1 chooses a move. Pass the device, then Player 2 chooses. Watch the results, and repeat until knockout.

## Rules

- Each character has HP, Attack, Defense, Speed, and a critical-hit chance.
- Both players secretly choose a move per round; **move priority** determines first attack, then **Speed** breaks ties. Tied speeds are randomized.
- **Quick** acts before **Heavy**; **Guard** reduces incoming damage; **Heavy** hits harder but acts last.
- Critical hits deal 1.5x damage. Defense reduces incoming damage.
- Each fighter charges their **own** Bounce Back meter as HP is lost. At 55 damage received, **Ultimate** unlocks, once per battle.
- Characters reset between matches.

## Scanner details and limitations

The browser crops just the central yellow guide plus 14% margin and sends a compressed ~420-pixel-wide image to OpenCV, then checks again ~95 ms after each response. Python OpenCV finds rectangular card contours, corrects perspective, checks the **rank-and-suit corner only**, and compares its red or dark symbol shapes with the supplied custom playing-card corner templates. No exact full-artwork image matching is necessary. The browser requires **2 matching detections in the most recent 3 frames** before it registers a card. The mapping is `J♥ → hearts_J`, `A♣ → clubs_A`. The game then displays the stored original artwork and stats in `data/cards.json`.

Unlike the old version, **there is no mandatory Capture click**. Use RECHECK NOW to immediately attempt a new scan if desired. Close the camera to stop streaming.

Recognition still requires a reasonably clear view of a *full card outline* and its rank/suit corner. This is a two-card-specific recognizer calibrated from the two supplied photos; it can be fooled by other playing cards with similar ink colors, so please test it with the actual cards before your presentation. Avoid glare, strong perspective tilt, and very small cards in the camera frame. Use Manual Test Mode if recognition isn't reliable. Scanner operates locally and does not upload camera data to a third-party service.

## File map

- `data/cards.json`: character database and move stats
- `static/cards/`: the **actual cropped playing-card photos**
- `static/index.html`, `static/style.css`, `static/app.js`: interactive game UI and combat engine
- `server.py`: webcam card detection endpoint and static file server
- `prep_cards.py`: regenerates cropped card art from `source/` photos

## Future improvements

To add more cards, add entries to `data/cards.json`, save their images, and extend the scanner's reference templates. For a full 52-card version, a general-purpose rank/suit detector or QR tags would scale better than feature-matching every artwork.

## Faster guided scanning

The yellow outline is the same region processed by the scanner. Hold the card directly in front of the Mac webcam, approximately filling the rectangle, with all four card corners visible and the rank/suit legible. The browser processes only that central region rather than searching the whole camera image. It still requires **two agreeing matches** before loading the character and offers Manual Test Mode if needed. Actual speed depends on your webcam, lighting and Mac.
