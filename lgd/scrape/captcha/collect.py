import sys
import time
import logging
from pathlib import Path

from lib import print_image_c

include_dir = str(Path(__file__).resolve().parents[1])
sys.path.append(include_dir)
from captcha_helper import CaptchaHelper
from base import get_context, BASE_URL

logger = logging.getLogger(__name__)

# captcha collection for testing
def collect_test_captchas(num_to_collect, captcha_helper):
    captcha_file_names = []
    for i in range(0, num_to_collect):
        logger.info('getting captcha image')
        captcha_content = captcha_helper.get_captcha(None)
        ctx.last_captcha = captcha_content
        captcha_file_name = captcha_helper.save_last_captcha(params, ctx)
        captcha_file_names.append(captcha_file_name)
        print_image_c(captcha_content)
        time.sleep(1)

if __name__ == '__main__':
    if len(sys.argv) > 0:
        num = int(sys.argv[0])
    else:
        num = 10

    ctx = get_context()
    captcha_helper = CaptchaHelper(ctx, BASE_URL)
    collect_test_captchas(num, captcha_helper)
