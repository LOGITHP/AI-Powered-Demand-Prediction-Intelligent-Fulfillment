export interface Worker {
  id: string;
  name: string;
  role: string;
  shift: string;
  status: 'PRESENT' | 'ABSENT' | 'AVAILABLE' | 'ON_TASK' | 'BREAK' | 'OFFLINE';
  currentTask?: string;
  workload?: number;
}
