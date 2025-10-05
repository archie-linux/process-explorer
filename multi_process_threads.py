import multiprocessing
import threading
import os
import time

# Function for a CPU-intensive task
def cpu_intensive_task(thread_id, process_id):
    print(f"Thread {thread_id} in Process {process_id} (PID {os.getpid()}) started.")
    result = 0
    while True:  # Simulate CPU work in a loop
        for i in range(1, 10000):
            result += i ** 2
        result %= 1000000  # Avoid overflow and keep the CPU busy

# Function to spawn threads in a child process
def spawn_threads(num_threads, process_id):
    print(f"Child Process {process_id} (PID {os.getpid()}) spawning {num_threads} threads.")
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=cpu_intensive_task, args=(i, process_id))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

# Child process function
def child_process(process_id):
    num_threads = 4  # Number of threads per child process
    spawn_threads(num_threads, process_id)

# Main function to spawn five child processes
if __name__ == "__main__":
    print(f"Parent Process PID {os.getpid()} spawning five child processes.")
    
    processes = []
    for process_id in range(5):  # Spawn five child processes
        process = multiprocessing.Process(target=child_process, args=(process_id,))
        processes.append(process)
        process.start()

    # Monitor child processes
    try:
        while any(process.is_alive() for process in processes):
            print(f"Child processes {[p.pid for p in processes if p.is_alive()]} are running.")
            time.sleep(2)
    except KeyboardInterrupt:
        print("Terminating child processes...")
        for process in processes:
            process.terminate()
    finally:
        for process in processes:
            process.join()
    
    print("Parent process exiting.")

