from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SurfaceADeliveryTests(unittest.TestCase):
    def test_primary_asset_is_served_cached_and_conversational(self):
        bootstrap=(ROOT/'ikant/bootstrap_http.py').read_text(encoding='utf-8')
        sw=(ROOT/'ikant/web/sw.js').read_text(encoding='utf-8')
        css=(ROOT/'ikant/web/bootstrap.css').read_text(encoding='utf-8')
        html=(ROOT/'ikant/web/index.html').read_text(encoding='utf-8')
        self.assertIn("'/conversation.js'",bootstrap)
        self.assertIn("/conversation.js",sw)
        self.assertIn('surface-a-hotfix4',sw)
        self.assertIn('primary-chat-output',css)
        self.assertIn('primary-chat-window',css)
        self.assertIn('/conversation.js',html)

if __name__=='__main__':unittest.main()
