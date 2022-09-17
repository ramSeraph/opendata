# The MIT License (MIT)
# 
# Copyright (c) 2016 Mahesh Venkitachalam
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.*
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.*


# original source: https://github.com/electronut/pp/blob/master/ascii/ascii.py

import io
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)
  
# 70 levels of gray
gscale1 = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
  
# 10 levels of gray
gscale2 = '@%#*+=-:. '

buf = []

def reset_buf():
    global buf
    buf = []

def print_buf():
    global buf
    for line in buf:
        logger.debug(line)
    reset_buf()

def print_l(line):
    global buf
    buf.append(line)


def getAverageL(image):

    """
    Given PIL Image, return average value of grayscale value
    """
    # get image as numpy array
    im = np.array(image)

    # get shape
    w,h = im.shape

    # get average
    return np.average(im.reshape(w*h))


# source: https://github.com/electronut/pp/blob/master/ascii/ascii.py
def convertImageToAscii(image, cols, scale, moreLevels):
    """
    Given Image and dims (rows, cols) returns an m*n list of Images
    """
    # declare globals
    global gscale1, gscale2

    # open image and convert to grayscale
    image = image.convert('L')

    # store dimensions
    W, H = image.size[0], image.size[1]
    #print_l("input image dims: %d x %d" % (W, H))

    # compute width of tile
    w = W/cols

    # compute tile height based on aspect ratio and scale
    h = w/scale

    # compute number of rows
    rows = int(H/h)

    #print_l("cols: %d, rows: %d" % (cols, rows))
    #print_l("tile dims: %d x %d" % (w, h))

    # check if image size is too small
    if cols > W or rows > H:
        print_l("Image too small for specified cols!")
        return []

    # ascii image is a list of character strings
    aimg = []
    # generate list of dimensions
    for j in range(rows):
        y1 = int(j*h)
        y2 = int((j+1)*h)

        # correct last tile
        if j == rows-1:
            y2 = H

        # append an empty string
        aimg.append("")
        for i in range(cols):
  
            # crop image to tile
            x1 = int(i*w)
            x2 = int((i+1)*w)
  
            # correct last tile
            if i == cols-1:
                x2 = W
  
            # crop image to extract tile
            img = image.crop((x1, y1, x2, y2))
  
            # get average luminance
            avg = int(getAverageL(img))
  
            # look up ascii char
            if moreLevels:
                gsval = gscale1[int((avg*69)/255)]
            else:
                gsval = gscale2[int((avg*9)/255)]
  
            # append ascii char to string
            aimg[j] += gsval
      
    # return txt image
    return aimg


def print_image_c(content, **kwargs):
    fp = io.BytesIO(content)
    img = Image.open(fp)
    print_image(img, **kwargs)


def print_image_np(img_np, **kwargs):
    img = Image.fromarray(img_np)
    print_image(img, **kwargs)


def print_image(img, cols=160, scale=1.0):
    aimg = convertImageToAscii(img, cols, 0.43, False)
    for row in aimg:
        print_l(row)


