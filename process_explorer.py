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
        self.process_tree = {}
        self.reverse_sort = True
        self.filter_string = ''
        self.show_threads = False
        self.tree_view = False
        self.selected_pid = None
        self.scroll_offset = 0

    def build_process_tree(self):
        # Initialize tree structure
        self.process_tree = defaultdict(list)
        pid_to_info = {}

        # Get all processes
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                       'status', 'create_time', 'num_threads', 'username', 'ppid']):
            try:
                proc_info = proc.info
                proc_info['cpu_percent'] = proc.cpu_percent()
                proc_info['memory_percent'] = proc.memory_percent()

                try:
                    proc_info['cmdline'] = ' '.join(proc.cmdline())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc_info['cmdline'] = '[Not accessible]'

                create_time = datetime.datetime.fromtimestamp(proc_info['create_time'])
                proc_info['age'] = str(datetime.datetime.now() - create_time).split('.')[0]

                if self.filter_string.lower() in proc_info['name'].lower():
                    pid = proc_info['pid']
                    ppid = proc_info.get('ppid', 0)
                    pid_to_info[pid] = proc_info
                    self.process_tree[ppid].append(pid)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return pid_to_info

    def get_process_info(self):
        if self.tree_view:
            return self.build_process_tree()
        else:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                           'status', 'create_time', 'num_threads', 'username']):
                try:
                    proc_info = proc.info
                    proc_info['cpu_percent'] = proc.cpu_percent()
                    proc_info['memory_percent'] = proc.memory_percent()

                    try:
                        proc_info['cmdline'] = ' '.join(proc.cmdline())
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        proc_info['cmdline'] = '[Not accessible]'

                    create_time = datetime.datetime.fromtimestamp(proc_info['create_time'])
                    proc_info['age'] = str(datetime.datetime.now() - create_time).split('.')[0]

                    if self.filter_string.lower() in proc_info['name'].lower():
                        processes.append(proc_info)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return processes

    def draw_tree_node(self, stdscr, pid, pid_to_info, depth=0, row=2, prefix=""):
        height, width = stdscr.getmaxyx()
        if row >= height - 1:
            return row

        proc_info = pid_to_info.get(pid)
        if not proc_info:
            return row

        # Calculate indentation
        indent = "  " * depth
        tree_symbol = "└─ " if prefix == "└─ " else "├─ "
        if depth == 0:
            tree_symbol = ""

        # Format process information
        line = (f"{indent}{tree_symbol}{proc_info['pid']:5d} {proc_info['name'][:20]:<20} "
               f"{proc_info['cpu_percent']:6.1f} {proc_info['memory_percent']:6.1f} "
               f"{proc_info['status'][:10]:<10} {proc_info['num_threads']:8d}")

        try:
            # Highlight selected process
            if self.selected_pid == proc_info['pid']:
                stdscr.addstr(row, 0, line[:width], curses.A_REVERSE)
            elif proc_info['cpu_percent'] > 50:
                stdscr.addstr(row, 0, line[:width], curses.A_BOLD)
            else:
                stdscr.addstr(row, 0, line[:width])
        except curses.error:
            pass

        row += 1

        # Draw children
        children = self.process_tree.get(pid, [])
        for i, child_pid in enumerate(children):
            is_last = (i == len(children) - 1)
            new_prefix = "└─ " if is_last else "├─ "
            row = self.draw_tree_node(stdscr, child_pid, pid_to_info, depth + 1, row, new_prefix)

        return row

    def draw_screen(self, stdscr):
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Draw header
        header = f" PID  {'NAME':<20} {'CPU%':>6} {'MEM%':>6} {'STATUS':<10} {'THREADS':>8} {'AGE':>12} {'USER':<15}"
        stdscr.addstr(0, 0, header[:width])
        stdscr.addstr(1, 0, "-" * (width-1))
        
        if self.tree_view:
            pid_to_info = self.processes
            root_pids = self.process_tree[0]  # Get top-level processes
            row = 2
            for pid in root_pids:
                row = self.draw_tree_node(stdscr, pid, pid_to_info, row=row)
        else:
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
                    
                    if self.selected_pid == proc['pid']:
                        stdscr.addstr(row, 0, line[:width], curses.A_REVERSE)
                    elif proc['cpu_percent'] > 50:
                        stdscr.addstr(row, 0, line[:width], curses.A_BOLD)
                    else:
                        stdscr.addstr(row, 0, line[:width])
                        
                    row += 1

                    if self.show_threads:
                        cmd = f"    └─ {proc['cmdline'][:width-6]}"
                        if row < height - 1:
                            stdscr.addstr(row, 0, cmd)
                            row += 1

                except curses.error:
                    pass

        # Draw footer with additional commands
        footer = (f" Sort: {self.sort_by} | Filter: {self.filter_string} | View: {'Tree' if self.tree_view else 'List'} | "
                 f"Selected PID: {self.selected_pid if self.selected_pid else 'None'} | "
                 f"Press: (c)pu (m)em (t)hreads (v)iew (f)ilter (k)ill ↑↓:select (q)uit")
        try:
            stdscr.addstr(height-1, 0, footer[:width], curses.A_REVERSE)
        except curses.error:
            pass

        stdscr.refresh()

    def terminate_process(self, pid):
        try:
            if pid:
                process = psutil.Process(pid)
                process.terminate()
                time.sleep(0.1)  # Give the process time to terminate
                if process.is_running():
                    process.kill()  # Force kill if still running
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
        return False

    def run(self, stdscr):
        curses.curs_set(0)
        stdscr.timeout(1000)

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
                elif key == ord('v'):
                    self.tree_view = not self.tree_view
                elif key == ord('f'):
                    curses.echo()
                    curses.curs_set(1)
                    stdscr.addstr(0, 0, "Filter: ")
                    self.filter_string = stdscr.getstr(0, 8).decode('utf-8')
                    curses.noecho()
                    curses.curs_set(0)
                elif key == ord('k'):
                    if self.selected_pid:
                        if self.terminate_process(self.selected_pid):
                            self.selected_pid = None
                elif key == curses.KEY_UP:
                    if not self.tree_view:
                        # Move selection up
                        if self.processes:
                            if self.selected_pid is None:
                                self.selected_pid = self.processes[-1]['pid']
                            else:
                                current_index = next((i for i, p in enumerate(self.processes) 
                                                    if p['pid'] == self.selected_pid), 0)
                                if current_index > 0:
                                    self.selected_pid = self.processes[current_index - 1]['pid']
                elif key == curses.KEY_DOWN:
                    if not self.tree_view:
                        # Move selection down
                        if self.processes:
                            if self.selected_pid is None:
                                self.selected_pid = self.processes[0]['pid']
                            else:
                                current_index = next((i for i, p in enumerate(self.processes) 
                                                    if p['pid'] == self.selected_pid), len(self.processes) - 1)
                                if current_index < len(self.processes) - 1:
                                    self.selected_pid = self.processes[current_index + 1]['pid']
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
