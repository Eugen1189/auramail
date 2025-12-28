import { useState, useEffect } from 'react'

function App() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch('/api/dashboard/data')
            .then(res => {
                if (res.status === 401) {
                    window.location.href = 'http://localhost:5000/authorize'
                    return null
                }
                return res.json()
            })
            .then(data => {
                if (data) {
                    setData(data)
                }
                setLoading(false)
            })
            .catch(err => {
                console.error(err)
                setLoading(false)
            })
    }, [])

    if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>

    return (
        <div className="container mx-auto p-8">
            <h1 className="text-3xl font-bold mb-8">
                Welcome back, <span className="text-aura-blue">{data?.user_email || 'User'}</span>
            </h1>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <h3 className="text-gray-400 mb-2">Total Emails</h3>
                    <p className="text-3xl font-bold">{data?.stats?.total_processed || 0}</p>
                </div>
                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <h3 className="text-gray-400 mb-2">Important</h3>
                    <p className="text-3xl font-bold text-aura-purple">{data?.stats?.important || 0}</p>
                </div>
                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <h3 className="text-gray-400 mb-2">Action Required</h3>
                    <p className="text-3xl font-bold text-aura-teal">{data?.stats?.action_required || 0}</p>
                </div>
            </div>

            <h2 className="text-2xl font-bold mb-4">Recent Activity</h2>
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                {data?.recent_activities?.map((act) => (
                    <div key={act.id} className="p-4 border-b border-gray-700 last:border-0 hover:bg-gray-700 transition">
                        <div className="flex justify-between">
                            <span className="font-semibold">{act.subject}</span>
                            <span className="text-sm text-gray-400">{act.timestamp}</span>
                        </div>
                        <div className="flex gap-2 mt-2 text-sm">
                            <span className="px-2 py-0.5 rounded bg-gray-600">{act.ai_category}</span>
                            <span className="px-2 py-0.5 rounded bg-blue-900 text-blue-200">{act.action_taken}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

export default App
