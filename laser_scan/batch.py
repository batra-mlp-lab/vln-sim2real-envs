

import subprocess

NUM = 16

if __name__ == '__main__':

    for ix in range(NUM):
        p=subprocess.Popen(['nodejs', 'LaserScan.js', str(ix), str(NUM)])
