import psutil
import time
import curses
import datetime
import argparse
from collections import defaultdict

class ProcessExplorer:
    def __init__(self):
        self.sort_by = 'cpu'
        self.processes = []
        self.reverse_sort = True
        self.filter_string = ''
        self.show_threads = False
        
    def get_process_info(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                       'status', 'create_time', 'num_threads', 'username']):
            try:
                # Get process info
                proc_info = proc.info
                proc_info['cpu_percent'] = proc.cpu_percent()
                proc_info['memory_percent'] = proc.memory_percent()
                
                # Get command line
                try:
                    proc_info['cmdline'] = ' '.join(proc.cmdline())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc_info['cmdline'] = '[Not accessible]'
                
                # Calculate process age
                create_time = datetime.datetime.fromtimestamp(proc_info['create_time'])
                proc_info['age'] = str(datetime.datetime.now() - create_time).split('.')[0]
                
                if self.filter_string.lower() in proc_info['name'].lower():
                    processes.append(proc_info)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        return processes

    def draw_screen(self, stdscr):
        # Clear screen
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Draw header
        header = f" PID  {'NAME':<20} {'CPU%':>6} {'MEM%':>6} {'STATUS':<10} {'THREADS':>8} {'AGE':>12} {'USER':<15}"
        stdscr.addstr(0, 0, header[:width])
        stdscr.addstr(1, 0, "-" * (width-1))
        
        # Sort processes
        self.processes.sort(key=lambda x: x.get(self.sort_by, 0), reverse=self.reverse_sort)
        
        # Draw processes
        row = 2
        for proc in self.processes:
            if row >= height - 1:
                break
                
            try:
                line = (f" {proc['pid']:5d} {proc['name'][:20]:<20} {proc['cpu_percent']:6.1f} "
                       f"{proc['memory_percent']:6.1f} {proc['status'][:10]:<10} {proc['num_threads']:8d} "
                       f"{proc['age']:>12} {proc['username'][:15]:<15}")
                
                if proc['cpu_percent'] > 50:  # Highlight high CPU usage
                    stdscr.addstr(row, 0, line[:width], curses.A_BOLD)
                else:
                    stdscr.addstr(row, 0, line[:width])
                    
                row += 1
                
                # Show command line if threads are enabled
                if self.show_threads:
                    cmd = f"    └─ {proc['cmdline'][:width-6]}"
                    if row < height - 1:
                        stdscr.addstr(row, 0, cmd)
                        row += 1
                        
            except curses.error:
                pass
        
        # Draw footer
        footer = (f" Sort: {self.sort_by} | Filter: {self.filter_string} | "
                 f"Press: (c)pu (m)em (t)hreads (f)ilter (q)uit")
        try:
            stdscr.addstr(height-1, 0, footer[:width], curses.A_REVERSE)
        except curses.error:
            pass
            
        stdscr.refresh()

    def run(self, stdscr):
        # Setup curses
        curses.curs_set(0)  # Hide cursor
        stdscr.timeout(1000)  # Set getch() timeout to 1 second
        
        while True:
            # Get updated process information
            self.processes = self.get_process_info()
            
            # Draw the screen
            self.draw_screen(stdscr)
            
            # Handle keyboard input
            try:
                key = stdscr.getch()
                if key == ord('q'):
                    break
                elif key == ord('c'):
                    self.sort_by = 'cpu_percent'
                    self.reverse_sort = True
                elif key == ord('m'):
                    self.sort_by = 'memory_percent'
                    self.reverse_sort = True
                elif key == ord('t'):
                    self.show_threads = not self.show_threads
                elif key == ord('f'):
                    curses.echo()
                    curses.curs_set(1)
                    stdscr.addstr(0, 0, "Filter: ")
                    self.filter_string = stdscr.getstr(0, 8).decode('utf-8')
                    curses.noecho()
                    curses.curs_set(0)
            except curses.error:
                pass

def main():
    parser = argparse.ArgumentParser(description='Terminal-based Process Explorer')
    parser.add_argument('-f', '--filter', help='Initial process name filter', default='')
    args = parser.parse_args()
    
    explorer = ProcessExplorer()
    explorer.filter_string = args.filter
    curses.wrapper(explorer.run)

if __name__ == '__main__':
    main()
