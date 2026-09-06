import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, AlertCircle, CheckCircle, Check, X } from 'lucide-react'
import { Button } from '../components/common/Button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { contractsApi } from '../services/api'
import { useContractStore } from '../store'

export function ContractResultsPage() {
  const { contractId } = useParams<{ contractId: string }>()
  const navigate = useNavigate()
  const { setContractResults, setReviewQueue, contractResults, uploadStatus, setUploadStatus } = useContractStore()
  const [results, setResults] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!contractId) return

    const pollStatus = async () => {
      try {
        while (true) {
          const status = await contractsApi.getStatus(contractId)
          if (status.status !== 'processing') {
            setUploadStatus(status.status as any)
            break
          }
          await new Promise(r => setTimeout(r, 3000))
        }

        const data = await contractsApi.getResults(contractId)
        setResults(data)
        setContractResults(data)
        if (data.risk_flags) {
          setReviewQueue(data.risk_flags.filter((f: any) => f.risk_level === 'critical' || f.risk_level === 'high' || !f.grounded))
        }
        setLoading(false)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load results')
        setLoading(false)
      }
    }

    pollStatus()
  }, [contractId, setContractResults, setReviewQueue, setUploadStatus])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 text-violet-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Analyzing contract...</p>
          <p className="text-sm text-slate-500 mt-2">Polling status every 3s</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Card className="max-w-md w-full mx-4">
          <CardContent className="text-center py-8">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Failed to load results</h2>
            <p className="text-slate-400 mb-6">{error}</p>
            <Button onClick={() => navigate('/contracts')}>Back to Upload</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!results) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center text-slate-400">No results found</div>
      </div>
    )
  }

  const { jurisdiction, clauses, risk_flags } = results

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Contract Analysis</h1>
            <p className="text-slate-400 mt-1">Contract ID: {contractId?.slice(0, 8)}...</p>
          </div>
          <Button onClick={() => navigate(`/contracts/${contractId}/review`)} disabled={!risk_flags?.length}>
            Review Queue ({risk_flags?.filter((f: any) => f.risk_level === 'critical' || f.risk_level === 'high' || !f.grounded).length || 0})
          </Button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Jurisdiction</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-slate-400">Country</p>
                <p className="text-lg font-medium text-white">{jurisdiction?.country || 'Unknown'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Region</p>
                <p className="text-lg font-medium text-white">{jurisdiction?.region || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Confidence</p>
                <p className="text-lg font-medium text-white">{(jurisdiction?.confidence * 100).toFixed(0)}%</p>
              </div>
            </div>
            {jurisdiction?.reasoning && (
              <p className="mt-4 text-sm text-slate-400">{jurisdiction.reasoning}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Extracted Clauses ({clauses?.length || 0})</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {clauses?.length === 0 ? (
              <p className="text-slate-500">No clauses extracted</p>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {clauses.map((clause: any) => (
                  <div key={clause.id} className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-white">{clause.title || 'Untitled'}</span>
                          <Badge variant="low">{clause.clause_type}</Badge>
                        </div>
                        <p className="text-sm text-slate-400 line-clamp-2">{clause.text}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Risk Flags ({risk_flags?.length || 0})</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {risk_flags?.length === 0 ? (
              <div className="text-center py-8">
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                <p className="text-slate-400">No risk flags detected</p>
              </div>
            ) : (
              <div className="space-y-4">
                {risk_flags.map((flag: any) => (
                  <div key={flag.clause_id} className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant={flag.risk_level}>{flag.risk_level.toUpperCase()}</Badge>
                          <Badge variant={flag.grounded ? 'success' : 'danger'}>
                            {flag.grounded ? (
                              <>
                                <Check className="h-3 w-3 mr-1" />
                                Grounded
                              </>
                            ) : (
                              <>
                                <X className="h-3 w-3 mr-1" />
                                Not Grounded
                              </>
                            )}
                          </Badge>
                        </div>
                        <p className="text-slate-300 mb-2">{flag.concern}</p>
                        {flag.suggested_redline && (
                          <p className="text-sm text-slate-400">
                            <span className="font-medium">Suggested redline:</span> {flag.suggested_redline}
                          </p>
                        )}
                        {flag.citation_ids?.length && (
                          <p className="text-xs text-slate-500 mt-1">
                            Citations: {flag.citation_ids.join(', ')}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}