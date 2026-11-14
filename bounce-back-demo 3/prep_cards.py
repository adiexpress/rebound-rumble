from pathlib import Path
import cv2, numpy as np
ROOT=Path(__file__).parent

def rectify(image):
    h,w=image.shape[:2]
    g=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(cv2.GaussianBlur(g,(7,7),0),40,120)
    contours,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    best=None; best_area=0
    for c in contours:
        area=cv2.contourArea(c)
        if area<0.035*w*h or area>0.85*w*h: continue
        p=cv2.approxPolyDP(c,0.026*cv2.arcLength(c,True),True)
        if len(p)!=4 or not cv2.isContourConvex(p): continue
        xy=p[:,0,:].astype('float32')
        side=np.linalg.norm(xy-np.roll(xy,1,axis=0),axis=1)
        if min(side)<70 or max(side)/min(side)>3: continue
        if area>best_area: best=xy;best_area=area
    if best is None: return None
    s=best.sum(axis=1); d=np.diff(best,axis=1).reshape(-1)
    tl=best[np.argmin(s)]; br=best[np.argmax(s)];tr=best[np.argmin(d)]; bl=best[np.argmax(d)]
    src=np.float32([tl,tr,br,bl]);target=np.float32([[0,0],[499,0],[499,699],[0,699]])
    return cv2.warpPerspective(image,cv2.getPerspectiveTransform(src,target),(500,700))

if __name__=='__main__':
    for src,target in [('IMG_3636.jpg','hearts_J'),('IMG_3633.jpg','clubs_A')]:
        original=cv2.imread(str(ROOT/'source'/src))
        image=rectify(original)
        if image is None: raise RuntimeError('Could not find card: '+src)
        cv2.imwrite(str(ROOT/'static/cards'/f'{target}.jpg'),image,[cv2.IMWRITE_JPEG_QUALITY,92])
        print('Saved',target)
