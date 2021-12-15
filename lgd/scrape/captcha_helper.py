import io
import copy
import time
import logging
from .captcha.lib import guess, print_buf, reset_buf

logger = logging.getLogger(__name__)


class CaptchaHelper:
    def __init__(self, params, ctx, base_url):
        self.params = params
        self.ctx = ctx
        self.last_captcha = None
        self.base_url = base_url

    def get_counter_filename(self):
        return 'captcha/data/test/counter'

    def save_last_captcha(self):
        content = self.last_captcha
        #TODO: use ctx to change location of files
        #TODO: add a lock
        counter_file_name = self.get_counter_filename()
        with open(counter_file_name) as f:
            counter = int(f.read())

        captcha_file_name = 'captcha/data/test/{}.png'.format(counter)
        with open(captcha_file_name, 'wb') as f:
            f.write(content)
        counter += 1
        with open(counter_file_name, 'w') as f:
            f.write(str(counter))
        return captcha_file_name


    def mark_failure(self):
        logger.warning('captcha guess failed')
        if self.params.save_all_captchas or self.params.save_failed_captchas:
            self.save_last_captcha()

        if self.params.print_captchas and logger.isEnabledFor(logging.DEBUG):
            print_buf()
        
    
    def mark_success(self):
        if self.params.save_all_captchas:
            self.save_last_captcha()
        reset_buf()
    
    
    def get_code(self, referer):
        captcha_content = self.get_captcha(referer)
        self.last_captcha = captcha_content
    
        logger.debug('parsing captcha')
        temp_file = io.BytesIO(captcha_content)
        captcha_code = guess(temp_file)
        logger.info('captcha code is: {}'.format(captcha_code))
        return captcha_code


    def get_captcha(self, referer):
        logger.info('getting captcha image')
        captcha_base_url = '{}/captchaImage'.format(self.base_url)
        captcha_url = '{}?{}'.format(captcha_base_url, round(time.time() * 1000))
        logger.debug(f'captcha url: {captcha_url}')
        web_data = self.ctx.session.get(captcha_url,
                                        headers={
                                            'referer': referer,
                                        },
                                        **self.params.request_args())
        if not web_data.ok:
            raise ValueError('bad web request.. {}: {}'.format(web_data.status_code, web_data.text))
        logger.info('got captcha image')
        return copy.copy(web_data.content)

