import { Scale, Wrench, Radar, Search } from 'lucide-react'

// One shared source for quick prompts: sidebar, top strip, hero, and command palette.
export const QUICK_PROMPTS = [
  {
    code: '01',
    label: 'Part 107 legality',
    hint: 'The over-people rule, decoded',
    query: 'Is flying over people legal under Part 107?',
    icon: Scale,
    keywords: 'faa regulation law people waiver',
  },
  {
    code: '02',
    label: 'Analyze flight log',
    hint: 'Find anomalies, open a ticket',
    query: 'Analyze the last flight log and open a maintenance ticket if needed',
    icon: Wrench,
    keywords: 'telemetry maintenance anomaly vibration ticket',
  },
  {
    code: '03',
    label: 'Plan a mission',
    hint: 'VX-6 endurance and risk',
    query: 'Can I fly the VX-6 on a 20-min inspection mission at 120m and what are the risks?',
    icon: Radar,
    keywords: 'flight plan mission endurance risk battery',
  },
  {
    code: '04',
    label: 'DGCA yellow zone',
    hint: 'Indian airspace permissions',
    query: 'What is required to fly a drone in a yellow zone in India?',
    icon: Search,
    keywords: 'india airspace permission dgca rules zone',
  },
]
