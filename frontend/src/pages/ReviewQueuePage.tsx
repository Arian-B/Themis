import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '../components/common/Button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { Modal } from '../components/common/Modal'
import { contractsApi } from '../services/api'
import { useContractStore } from '../store'

export function ReviewQueuePage() {
  const { contractId } = useParams<{ contractId: string }>()
  const navigate = useNavigate()
  const { reviewQueue, setReviewQueue } = useContractStore()
  const [queue, setQueue] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [confirmDialog, setConfirmDialog] = useState<{ flagId: string; decision: 'accepted' | 'rejected' } | null>(null)

  useEffect(() => {
    if (!contractId) return

    const loadQueue = async () => {
      try {
        const data = await contractsApi.getReviewQueue(contractId)
        setQueue(data.queue || [])
        setReviewQueue(data.queue || [])
        setLoading(false)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load review queue')
        setLoading(false)
      }
    }

    loadQueue()
  }, [contractId, setReviewQueue])

  const handleSubmit = async (flagId: string, decision: 'accepted' | 'rejected') => {
    if (!contractId) return
    setSubmitting(flagId)
    try {
      await contractsApi.submitReview(contractId, { flag_id: flagId, decision })
      setQueue(prev => prev.filter(f => f.clause_id !== flagId))
      setReviewQueue(prev => prev?.filter(f => f.clause_id !== flagId) || [])
      setConfirmDialog(null)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit review')
    } finally {
      setSubmitting(null)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="h-12 w-12 text-violet-500 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Card className="max-w-md w-full mx-4">
          <CardContent className="text-center py-8">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Failed to load review queue</h2>
            <p className="text-slate-400 mb-6">{error}</p>
            <Button onClick={() => navigate(`/contracts/${contractId}`)}>Back to Results</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Review Queue</h1>
            <p className="text-slate-400 mt-1">Contract ID: {contractId?.slice(0, 8)}...</p>
          </div>
          <Button onClick={() => navigate(`/contracts/${contractId}`)} variant="ghost">
            ← Back to Results
          </Button>
        </div>

        {queue.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No items in review queue</h3>
              <p className="text-slate-400">All risk flags have been reviewed or are low-risk/grounded.</p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Pending Review Items ({queue.length})</CardTitle>
              <CardDescription>
                High-risk or ungrounded flags requiring human decision
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {queue.map((item: any) => (
                  <div key={item.clause_id} className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant={item.risk_level}>{item.risk_level.toUpperCase()}</Badge>
                          <Badge variant={item.grounded ? 'success' : 'warning'}>
                            {item.grounded ? 'Grounded' : 'Not Grounded'}
                          </Badge>
                        </div>
                        <p className="text-slate-300">{item.concern}</p>
                        <p className="text-xs text-slate-500 mt-1">Clause: {item.clause_id.slice(0, 8)}...</p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setConfirmDialog({ flagId: item.clause_id, decision: 'accepted' })}
                          disabled={submitting === item.clause_id}
                        >
                          Accept
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => setConfirmDialog({ flagId: item.clause_id, decision: 'rejected' })}
                          disabled={submitting === item.clause_id}
                        >
                          Reject
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Modal
          isOpen={!!confirmDialog}
          onClose={() => setConfirmDialog(null)}
          title="Confirm Decision"
          description={`Are you sure you want to ${confirmDialog?.decision} this flag?`}
          size="sm"
        >
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="ghost" onClick={() => setConfirmDialog(null)}>
              Cancel
            </Button>
            <Button
              variant={confirmDialog?.decision === 'accepted' ? 'primary' : 'danger'}
              onClick={() => confirmDialog && handleSubmit(confirmDialog.flagId, confirmDialog.decision)}
              disabled={!!submitting}
            >
              {submitting ? 'Submitting...' : `Confirm ${confirmDialog?.decision}`}
            </Button>
          </div>
        </Modal>
      </div>
    </div>
  )
}