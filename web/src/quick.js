import { Scale, Wrench, Radar, Search } from 'lucide-react'

// One shared source for quick prompts: sidebar, top strip, and empty state.
export const QUICK_PROMPTS = [
  {
    label: 'Part 107 legality',
    hint: 'Over-people rule',
    query: 'Is flying over people legal under Part 107?',
    icon: Scale,
  },
  {
    label: 'Analyze flight log',
    hint: 'Find anomalies + open ticket',
    query: 'Analyze the last flight log and open a maintenance ticket if needed',
    icon: Wrench,
  },
  {
    label: 'Plan a mission',
    hint: 'VX-6 endurance & risk',
    query: 'Can I fly the VX-6 on a 20-min inspection mission at 120m and what are the risks?',
    icon: Radar,
  },
  {
    label: 'DGCA yellow zone',
    hint: 'Indian drone rules',
    query: 'What is required to fly a drone in a yellow zone in India?',
    icon: Search,
  },
]
