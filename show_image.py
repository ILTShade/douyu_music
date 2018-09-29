import cv2
while True:
    log = input()
    print(log)
    if log == '保存图片成功':
        cv2.imshow('music', cv2.imread('image/background.jpg'))
        cv2.waitKey(10)
        print('显示图片成功')

