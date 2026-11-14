"""Lightweight two-card recognizer for the custom Haven J♥ / A♣ deck.

Only compares the *printed rank-and-suit corner*; the artwork isn't used for ID.
Frames come from the browser and the server returns one prediction per frame.
Browser-side voting avoids a single noisy frame triggering a registration.
"""
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).parent
CARD_IDS = ("hearts_J", "clubs_A")

# A custom-deck corner reference, as photographed in the original project.
REFS = {id: cv2.imread(str(ROOT / 'static' / 'cards' / f'{id}.jpg')) for id in CARD_IDS}


def _card_candidates(image):
    """Try both threshold and edge outlines, then perspective-correct rectangular cards."""
    h, w = image.shape[:2]
    ratio = max(h, w) / 1100
    if ratio > 1:
        image = cv2.resize(image, (int(w / ratio), int(h / ratio)))
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 35, 105)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    adaptive = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY_INV, 35, 8)
    results = []
    seen = set()
    for binary in [edges, adaptive]:
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:55]:
            area = cv2.contourArea(contour)
            if not (.025 * h * w <= area <= .96 * h * w):
                continue
            peri = cv2.arcLength(contour, True)
            quad = cv2.approxPolyDP(contour, .025 * peri, True)
            if len(quad) != 4 or not cv2.isContourConvex(quad):
                continue
            p = quad[:, 0, :].astype(np.float32)
            sides = np.linalg.norm(p - np.roll(p, 1, axis=0), axis=1)
            if min(sides) < 40 or max(sides) / min(sides) > 2.8:
                continue
            cx,cy = np.mean(p,axis=0)
            signature = (round(cx / 30), round(cy / 30), round(area / 1500))
            if signature in seen:
                continue
            seen.add(signature)
            s = p.sum(axis=1)
            diff = np.diff(p, axis=1).flatten()
            pts = np.float32([p[np.argmin(s)], p[np.argmin(diff)], p[np.argmax(s)], p[np.argmax(diff)]])
            # Warp in portrait orientation for an upright or upside-down card.
            width = (np.linalg.norm(pts[1] - pts[0]) + np.linalg.norm(pts[2] - pts[3])) / 2
            height = (np.linalg.norm(pts[3] - pts[0]) + np.linalg.norm(pts[2] - pts[1])) / 2
            if width > height:
                # Rotate the rectified landscape version to portrait.
                dst = np.float32([[0, 0], [699, 0], [699, 499], [0, 499]])
                warped = cv2.warpPerspective(image, cv2.getPerspectiveTransform(pts, dst), (700, 500))
                warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
            else:
                dst = np.float32([[0, 0], [499, 0], [499, 699], [0, 699]])
                warped = cv2.warpPerspective(image, cv2.getPerspectiveTransform(pts, dst), (500, 700))
            results.append((area, warped))
            if len(results) >= 7:
                break
        if results:
            break
    results.sort(key=lambda pair: pair[0], reverse=True)
    return [card for _, card in results[:4]]


def _corner_features(card):
    """Extract small symbols from the upper-left printed corner only."""
    corner = card[14:157, 18:118]
    hsv = cv2.cvtColor(corner, cv2.COLOR_BGR2HSV)
    # red ink for J♥; black ink for A♣; robust to illumination.
    red = cv2.inRange(hsv, (0, 55, 45), (16, 255, 255)) | cv2.inRange(hsv, (165, 55, 45), (179, 255, 255))
    dark = cv2.inRange(hsv, (0, 0, 0), (179, 255, 105))
    gray = cv2.cvtColor(corner, cv2.COLOR_BGR2GRAY)
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, 21, 9)
    # Rank is top portion, suit is below it. We compare individual symbols
    # against *both* stored corner references, not the full illustration.
    return red, dark, ink


def _similarity(a, b):
    # Blur/resize allows more tolerance than exact pixel matching.
    a = cv2.resize(a, (50, 72), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    b = cv2.resize(b, (50, 72), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    a = cv2.GaussianBlur(a, (3, 3), 0)
    b = cv2.GaussianBlur(b, (3, 3), 0)
    # Balanced overlap metric avoids matching a blank/light corner.
    overlap = np.minimum(a, b).sum()
    union = np.maximum(a, b).sum()
    return float(overlap / (union + 1e-6))


REF_MASKS = {key: _corner_features(img) for key, img in REFS.items()}


def _recognize(card):
    best = None
    for rotation in (card, cv2.rotate(card, cv2.ROTATE_180)):
        masks = _corner_features(rotation)
        red_count = int(cv2.countNonZero(masks[0]))
        dark_count = int(cv2.countNonZero(masks[1]))
        # Corners without enough colored/black ink should not be classified.
        if max(red_count, dark_count) < 100:
            continue
        scores = {}
        for key, reference in REF_MASKS.items():
            # Color/shape of *both* symbols rather than artwork resemblance.
            channel = 0 if key == 'hearts_J' else 1
            shape = _similarity(masks[channel], reference[channel])
            color_count = red_count if channel == 0 else dark_count
            other_count = dark_count if channel == 0 else red_count
            color_dominance = color_count / max(1, color_count + other_count)
            scores[key] = .65 * shape + .35 * color_dominance
        key = max(scores, key=scores.get)
        score = scores[key]
        other = scores[next(k for k in scores if k != key)]
        # A predicted card MUST have clearly matching corner marks; abstain
        # when the rank/suit cannot be read. Multi-frame vote happens in JS.
        if score >= .35 and score - other >= .075:
            if best is None or score > best[1]:
                best = (key, score, scores)
    return best


def detect_card(image):
    candidates = _card_candidates(image)
    if not candidates:
        return {'ok': False, 'message': 'Looking for a card outline… Place one card in view.'}
    winner = None
    for c in candidates:
        result = _recognize(c)
        if result and (winner is None or result[1] > winner[1]):
            winner = result
    if winner is None:
        return {'ok': False, 'message': 'Card found — move the rank and suit closer to the camera.'}
    key, score, scores = winner
    return {'ok': True, 'cardId': key,
            'label': 'J♥' if key == 'hearts_J' else 'A♣',
            'confidence': round(score, 3)}


def detect_guided_card(image):
    """Fast recognition for a webcam crop roughly aligned to a 5:7 guide.

    The crop still includes a little background so a card silhouette can be
    located and perspective-corrected. Unlike full-frame scanning, OpenCV
    only searches a small (~420px wide) region of interest.
    """
    # Downscaling large frames is handled by the browser, but tolerate API use.
    h, w = image.shape[:2]
    if w > 520:
        k = 520 / w
        image = cv2.resize(image, (520, round(h*k)))
    cards = _card_candidates(image)
    best = None
    for card in cards[:2]:
        result = _recognize(card)
        if result and (best is None or result[1] > best[1]):
            best = result
    if best is None:
        return {'ok': False, 'message': 'Align the entire card with the yellow box; keep the corner symbols clear.'}
    key, score, _ = best
    return {'ok': True, 'cardId': key,
            'label': 'J♥' if key == 'hearts_J' else 'A♣',
            'confidence': round(score, 3)}

# A guide-aligned card may touch the crop edges, making its outline impossible
# to contour. Also try the rectangular region directly at a few tolerances.
# For the two-card demo this is much cheaper than a full-frame contour search.
_old_guided_detection = detect_guided_card

def detect_guided_card(image):
    h,w=image.shape[:2]
    if w>520:
        image=cv2.resize(image,(520,round(h*520/w)))
        h,w=image.shape[:2]
    candidates=[]
    # With a 14% larger camera crop, a correctly aligned card occupies about
    # 88% of the image. Accommodate cards that aren't perfectly centered.
    for fraction in (0.88,0.95,0.78):
        crop_w=int(w*fraction)
        crop_h=int(h*fraction)
        for dx,dy in ((0,0),(-.035,-.035),(.035,.035)):
            cx=int(w*(.5+dx));cy=int(h*(.5+dy))
            x=max(0,min(w-crop_w,cx-crop_w//2))
            y=max(0,min(h-crop_h,cy-crop_h//2))
            crop=image[y:y+crop_h,x:x+crop_w]
            if crop.size:
                candidates.append(cv2.resize(crop,(500,700)))
    # Add a few corrected quadrilaterals when a full outline is visible.
    candidates.extend(_card_candidates(image)[:2])
    best=None
    for candidate in candidates:
        result=_recognize(candidate)
        if result and (best is None or result[1]>best[1]):
            best=result
    if best is None:
        return {'ok':False,'message':'Place the card within the outline, keeping the top-left rank and suit visible.'}
    key,score,_=best
    return {'ok':True,'cardId':key,'label':'J♥' if key=='hearts_J' else 'A♣','confidence':round(score,3)}
