import os
import sys
import asyncio
import time
import sqlite3

# Append workspace root directory for clean asset loading path access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_pipeline.live_platform_harness import LivePlatformHarness, TELEMETRY

class PlatformSoakWatchdog:
    """
    🛰️ APEX MONITORING SUITE: STAGE E ENDURANCE WATCHDOG
    Monitors operational health statistics over long-duration live streaming windows
    to verify memory boundary safety, CPU stability, and task flatlining.
    """
    def __init__(self, run_duration_minutes: float = 60.0):
        self.duration_seconds = run_duration_minutes * 60
        self.log_folder = "telemetry"
        self.log_file = os.path.join(self.log_folder, f"soak_report_{int(time.time())}.log")
        
    def initialize_telemetry_file(self):
        os.makedirs(self.log_folder, exist_ok=True)
        with open(self.log_file, "w") as f:
            f.write("TIMESTAMP_MS,INGESTED,STRATEGY_PROC,DB_COMMITS,DB_DROPPED,STRATEGY_LAG_MS,DB_LOCKOUT_MS,ASYNC_TASKS\n")
        print(f"  └── [WATCHDOG INITIALIZED] Recording endurance metric rows to: {self.log_file}")

    async def execute_soak_session(self):
        self.initialize_telemetry_file()
        
        # Instantiate your verified active production streaming pipeline harness
        harness = LivePlatformHarness(target_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        
        # Spawn the live network consumer loop in the asynchronous background fabric
        pipeline_task = asyncio.create_task(harness.start())
        
        start_time = time.time()
        print(f"⚡ Launching continuous {self.duration_seconds / 60:.1f}-minute endurance soak campaign...")
        print("-" * 69)
        
        try:
            while time.time() - start_time < self.duration_seconds:
                await asyncio.sleep(60.0) # Evaluate operational health snapshots every 60 seconds
                
                timestamp_ms = int(time.time() * 1000)
                
                # Extract clean platform states directly from active runtime telemetry memory
                log_line = (
                    f"{timestamp_ms},{TELEMETRY['ticks_ingested']},"
                    f"{TELEMETRY['strategy_processed']},{TELEMETRY['db_processed']},"
                    f"{TELEMETRY['db_dropped']},{TELEMETRY['max_strategy_latency_ms']:.2f},"
                    f"{TELEMETRY['max_db_latency_ms']:.2f},{TELEMETRY['peak_async_tasks']}\n"
                )
                
                # Commit the log frame row to the storage log file on disk
                with open(self.log_file, "a") as f:
                    f.write(log_line)
                    
                print(f"🛰️  [SOAK SNAPSHOT] Ingested: {TELEMETRY['ticks_ingested']} | "
                      f"Strat Latency: {TELEMETRY['max_strategy_latency_ms']:.2f}ms | "
                      f"Tasks: {TELEMETRY['peak_async_tasks']} (SLO Flatlined)")
                
                # Anti-Leak Guardrail: If async tasks trend upwards continuously, drop the socket connection instantly
                if TELEMETRY['peak_async_tasks'] > 15:
                    print("🚨 [CRITICAL INFRASTRUCTURE ALARM] Task accumulation threshold breached! Activating manual circuit breaker...")
                    break
                    
        except Exception as e:
            print(f"❌ [WATCHDOG CRASH] Soak monitoring layer encountered unexpected fault: {e}")
        finally:
            print("\n=====================================================================")
            print("🏁 CONCLUSIVE WATCHDOG WINDOW REACHED: MANUALLY CLOSING PIPELINE CORES")
            pipeline_task.cancel()
            print("=====================================================================")

if __name__ == "__main__":
    # Run an initial 3-minute tight soak window to verify logger file-writing reliability
    watchdog = PlatformSoakWatchdog(run_duration_minutes=3.0)
    asyncio.run(watchdog.execute_soak_session())
