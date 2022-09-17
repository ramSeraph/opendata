import re
import logging

from PIL import Image, ImageOps
import pytesseract
import numpy as np

from scipy import ndimage

from skimage import measure
from skimage.segmentation import watershed
from skimage.feature import peak_local_max

from .print import print_l, print_image

logger = logging.getLogger(__name__)

def threshold(value, i):
    """
    dependig to the value of i and value assigne or 0 or 255 can take a single
    value or a tuple of two element
    """

    if (isinstance(value, tuple)):
        if i > value[0] and i <= value [1]:
            return 255
        else:
            return 0

    if value < i:
        return 255
    else:
        return 0


def thresholding(img, lower, upper):
    bw = np.asarray(img).copy()
    bw[bw < lower] = 0    # Black
    bw[bw >= upper] = 255 # White
    return Image.fromarray(bw)



def remove_transparency(im, bg_colour=(255, 255, 255)):

    # Only process if image has transparency (http://stackoverflow.com/a/1963146)
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):

        # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
        alpha = im.convert('RGBA').split()[-1]

        # Create a new background image of our matt color.
        # Must be RGBA because paste requires both images have the same format
        # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
        bg = Image.new("RGBA", im.size, bg_colour + (255,))
        bg.paste(im, mask=alpha)
        return bg
    else:
        return im


def merge(entry1, entry2):
    # The new image bounding box.
    bbox = (min([entry1['bbox'][0], entry2['bbox'][0]]),
            min([entry1['bbox'][1], entry2['bbox'][1]]),
            max([entry1['bbox'][2], entry2['bbox'][2]]),
            max([entry1['bbox'][3], entry2['bbox'][3]]))

    # The new image shape.
    shape = (bbox[2] - bbox[0], bbox[3] - bbox[1])

    # The slice for image 1 inside of the new image array.
    img1_slice = (slice(entry1['bbox'][0] - bbox[0], entry1['bbox'][2] - bbox[0]),
                  slice(entry1['bbox'][1] - bbox[1], entry1['bbox'][3] - bbox[1]))

    # The slice for image 2 inside of the new image array.
    img2_slice = (slice(entry2['bbox'][0] - bbox[0], entry2['bbox'][2] - bbox[0]),
                  slice(entry2['bbox'][1] - bbox[1], entry2['bbox'][3] - bbox[1]))

    # Construct the new image, and fill it with white.
    merged_image = np.empty(shape, dtype=bool)
    merged_image.fill(False)

    # Use all of image 1 and just drop it into the correct location within the new image.
    merged_image[img1_slice] = entry1['img']

    # We can't use the same approach for image 2, as it potentially overlaps with image 1.
    # Instead we use the parts of image 2 that aren't at the maximum of each color channel.
    merged_image[img2_slice] = np.where(entry2['img'] != False, entry2['img'],
                                        merged_image[img2_slice])

    props = measure.regionprops(merged_image.astype(np.uint8))
    print_l('found {} labels'.format(len(props)))
    centroid = props[0].centroid
    centroid = (centroid[0] + bbox[0], centroid[1] + bbox[1])
    return { 'img': merged_image, 'bbox': bbox, 'centroid': centroid, 'area': props[0].area, 'merged': True, 'split': False }


def split(entry):
    image = entry['img']
    image = image.astype(np.uint8)
    distance = ndimage.distance_transform_edt(image)
    coords = peak_local_max(distance, num_peaks=2, labels=image)
    mask = np.zeros(distance.shape, dtype=bool)
    mask[tuple(coords.T)] = True
    markers, _ = ndimage.label(mask)
    labels = watershed(-distance, markers, mask=image)
    props = measure.regionprops(labels)
    if len(props) != 2:
        print_l('expected 2 props, got {}'.format(len(props)))
    for prop in props:
        print_image(Image.fromarray(prop.image), cols=10)
    
    p_bbox = entry['bbox']
    entries = []
    for i in range(0,min(2, len(props))):
        prop = props[i]
        centroid = prop.local_centroid
        l_bbox = prop.bbox
        bbox = (l_bbox[0] + p_bbox[0],
                l_bbox[1] + p_bbox[1],
                l_bbox[2] + p_bbox[0],
                l_bbox[3] + p_bbox[1])
        centroid = (centroid[0] + bbox[0], centroid[1] + bbox[1])
        p_img = prop.image.astype(bool)
        entries.append({ 'img': p_img, 'centroid': prop.centroid, 'bbox': bbox, 'area': prop.area, 'merged': False, 'split': True })
    
    entries.sort(key=lambda x: x['bbox'][1])
    return entries


def find_splits(char_images, mode, threshold):
    dim = 0 if mode == 'vertical' else 1
    split_char_images = []
    for char_entry in char_images:
        # no horizontal and vertical splits on the same piece
        if char_entry['split']:
            split_char_images.append(char_entry)
            continue
        prop_image = char_entry['img']
        dim_extent = prop_image.shape[dim]
        #print(prop_image.shape)
        if dim_extent > threshold:
            print_l('splitting image {}ly'.format(mode))
            #convexhull_split(char_entry, mode)
            char_entries = split(char_entry)
            for entry in char_entries:
                split_char_images.append(entry)
        else:
            split_char_images.append(char_entry)
    return split_char_images


def find_vertical_splits(char_images):
    return find_splits(char_images, 'vertical', 40)


def find_horizontal_splits(char_images):
    return find_splits(char_images, 'horizontal', 38)


def merge_close_ones(char_images):
    while True:
        num_changes = 0
        num = len(char_images)
        merged_char_images = []
        i = 0
        while True:
            if i >= num:
                break
            char_entry = char_images[i]
            if i >= num - 1: 
                merged_char_images.append(char_entry)
                break
            char_entry_next = char_images[i+1]

            if abs(char_entry['centroid'][1] - char_entry_next['centroid'][1]) > 5:
                merged_char_images.append(char_entry)
                i += 1
            else:
                print_l('merging entries')
                merged_char_images.append(merge(char_entry, char_entry_next))
                num_changes += 1
                i += 2
        if num_changes == 0:
            break
        char_images = merged_char_images
    return char_images


def add_base_data(char_images):
    print_l('collecting bases')
    #bases = [[],[]]
    avg_bases = [0,0]
    for i, char_entry in enumerate(char_images):
        bbox = char_entry['bbox']
        base = bbox[2]
        if i < 3:
            char_entry['line'] = 0
            avg_bases[0] += base
        else:
            char_entry['line'] = 1
            avg_bases[1] += base
    avg_bases = [ x/3 for x in avg_bases ]
    num_below = [0, 0]
    for char_entry in char_images:
        bbox = char_entry['bbox']
        base = bbox[2]
        line = char_entry['line']
        avg_base = avg_bases[line]
        if base - avg_base >= 0:
            num_below[line] += 1


    for char_entry in char_images:
        bbox = char_entry['bbox']
        base = bbox[2]
        line = char_entry['line']
        threshold = 3
        if num_below[line] == 2:
            threshold = 2

        avg_base = avg_bases[line]
        if base - avg_base >= threshold:
            print_l('marking as below: {}, {}'.format(base, avg_base))
            char_entry['below'] = True
        else:
            char_entry['below'] = False


def guess(filename, models_dir):
    tessdir_base = models_dir

    tessdir_old = tessdir_base + '/old'
    tessdir_new = tessdir_base + '/lstm'

    image = Image.open(filename)
    #print_image(image)
    image = remove_transparency(image)
    image = image.convert('RGB')
    image = image.convert('L')
    image = thresholding(image, 128, 128)
    image = image.transform(
            image.size,
            Image.AFFINE,
            (1, -0.14775, 0, 0, 1, 0), resample=Image.BICUBIC, fillcolor=0)
    print_image(image)
    np_image = np.array(image)
    label_img = measure.label(np_image, connectivity=2)
    props = measure.regionprops(label_img)
    char_images = []
    for prop in props:
        if prop.area < 20:
            continue
        char_images.append({ 'img': prop.image, 'centroid': prop.centroid, 'bbox': prop.bbox, 'area': prop.area, 'merged': False, 'split': False })

    # sort char images based on horizontal location
    char_images.sort(key=lambda x: x['centroid'][1])

    # merge close centroids
    char_images = merge_close_ones(char_images)

    char_images = find_vertical_splits(char_images)
    char_images = find_horizontal_splits(char_images)


    found_all = True
    if len(char_images) != 6:
        print_l('Unexpected number of char images: {}'.format(len(char_images)))
        print_l('{}'.format([ (x['area'], x['centroid']) for x in char_images]))
        found_all = False

    if found_all:
        add_base_data(char_images)

    prediction = ''
    for char_entry in char_images:
        prop_image = char_entry['img']
        print_l('{}'.format(prop_image.shape))
        print_l('{}'.format(char_entry['bbox']))
        print_l('area: {}'.format(char_entry['area']))
        height = prop_image.shape[0]
        width = prop_image.shape[1]
        prop_image = np.pad(array=prop_image, pad_width=4, mode='constant', constant_values=False)
        char_image = Image.fromarray(prop_image)
        char_image = char_image.convert('L')
        char_image = ImageOps.invert(char_image)
        #char_image = ImageOps.scale(char_image, 0.9, resample=Image.BICUBIC)
        print_image(char_image, cols=(char_entry['bbox'][3] - char_entry['bbox'][1]))
        config_base = ' --oem {} --psm 10 --tessdata-dir "{}" configfile myconfig'
        config_old = config_base.format(0, tessdir_old)
        config_new = config_base.format(1, tessdir_new)
        char = pytesseract.image_to_string(char_image, config=config_old)
        print_l('guessed {}'.format(char))
        char = re.sub('[^a-zA-Z0-9]', '', char)
        if char == '':
            char = pytesseract.image_to_string(char_image, config=config_new)
            print_l('guessed {} with new'.format(char))
            char = re.sub('[^a-zA-Z0-9]', '', char)
            if len(char) > 1:
                char = char[:1]

        if char == 'l' and char_entry['merged']:
            print_l('correcting "l" to "i" for merged character')
            char = 'i'
        if char == '1' and char_entry['merged']:
            print_l('correcting "1" to "j" for merged character')
            char = 'j'

        if found_all:
            if char == 'p' and not char_entry['below']:
                print_l('correcting "p" to "P" for non-dipped character')
                char = 'P'

            if char == 'P' and char_entry['below']:
                print_l('correcting "P" to "p" for dipped character')
                char = 'p'
            if char == 'Y' and char_entry['below']:
                print_l('correcting "Y" to "y" for dipped character')
                char = 'y'
            if char == '9' and char_entry['below']:
                print_l('correcting "9" to "g" for dipped character')
                char = 'g'
            if char == 'i' and char_entry['below']:
                print_l('correcting "i" to "j" for dipped character')
                char = 'j'


        if char == '0' and width > 25:
            print_l('correcting "0" to "O" based on width')
            char = 'O'

        if height < 25 and char.isupper():
            print_l('correcting "{}" to lower based on height'.format(char))
            char = char.lower()

        if char == 'O' and width < 25:
            print_l('correcting "O" to "0" based on width')
            char = '0'

        if char == 'I' and width <= 8:
            print_l('correcting "I" to "l" based on width')
            char ='l'

        if char == '' and not char_entry['split'] and not char_entry['merged'] and char_entry['area'] > 100:
            print_l('correcting "" to "l" based on area')
            char ='l'

        prediction += char

    #image = ImageOps.invert(image)
    #config = ' --oem 1 --psm 11 --tessdata-dir "." configfile myconfig'
    #captcha_code = pytesseract.image_to_string(image, config=config)
    #captcha_code = re.sub('[^a-zA-Z0-9]', '', captcha_code)

    return prediction

