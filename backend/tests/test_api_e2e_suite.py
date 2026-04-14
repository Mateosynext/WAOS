import subprocess, sys, unittest
from pathlib import Path
class ApiE2ESuiteTest(unittest.TestCase):
    def test_api_e2e_script(self):
        root = Path(__file__).resolve().parents[1]
        script = root / 'scripts' / 'run_api_e2e.py'
        result = subprocess.run([sys.executable, str(script)], cwd=str(root.parents[0]), capture_output=True, text=True)
        if result.returncode != 0:
            self.fail(f'API e2e script failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}')
        self.assertIn('API E2E flows passed', result.stdout)
if __name__ == '__main__':
    unittest.main()
