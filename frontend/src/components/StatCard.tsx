import clsx from 'clsx'

interface StatCardProps {
  title: string
  value: string | number
  icon?: string
  color?: 'blue' | 'green' | 'purple' | 'orange'
}

export default function StatCard({ title, value, icon = '📊', color = 'blue' }: StatCardProps) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-900 border-blue-200',
    green: 'bg-green-50 text-green-900 border-green-200',
    purple: 'bg-purple-50 text-purple-900 border-purple-200',
    orange: 'bg-orange-50 text-orange-900 border-orange-200',
  }

  return (
    <div className={clsx('rounded-lg p-6 border', colorClasses[color])}>
      <div className="text-3xl mb-2">{icon}</div>
      <p className="text-sm font-medium opacity-75">{title}</p>
      <p className="text-3xl font-bold mt-2">{value}</p>
    </div>
  )
}
