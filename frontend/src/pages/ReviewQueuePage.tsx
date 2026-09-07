import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, AlertCircle, CheckCircle, XCircle, ArrowLeft, Check, X } from 'lucide-react'
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
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <Loader2 className="h-12 w-12 text-blue-500 animate-spin" />
        </motion.div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card className="max-w-md w-full mx-4 elevated" padding="lg">
            <CardContent className="text-center py-4">
              <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-slate-50 mb-2">Failed to load review queue</h2>
              <p className="text-slate-400 mb-6">{error}</p>
              <Button onClick={() => navigate(`/contracts/${contractId}`)} iconLeft={<ArrowLeft className="h-4 w-4" />}>
                Back to Results
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4 md:py-12">
      <AnimatePresence mode="popLayout">
        <motion.div
          key={contractId}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
          className="max-w-3xl mx-auto space-y-6 px-4"
        >
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col md:flex-row md:items-center md:justify-between gap-4"
          >
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-slate-50">Review Queue</h1>
              <p className="text-slate-400 mt-1">Contract ID: <span className="font-mono text-slate-300">{contractId?.slice(0, 8)}...</span></p>
            </div>
            <Button onClick={() => navigate(`/contracts/${contractId}`)} variant="ghost" iconLeft={<ArrowLeft className="h-4 w-4" />}>
              Back to Results
            </Button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            layout
          >
            {queue.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
              >
                <Card elevated padding="lg">
                  <CardContent className="text-center py-8">
                    <CheckCircle className="h-16 w-16 text-emerald-500 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-slate-50 mb-2">No items in review queue</h3>
                    <p className="text-slate-400">All risk flags have been reviewed or are low-risk/grounded.</p>
                  </CardContent>
                </Card>
              </motion.div>
            ) : (
              <Card elevated padding="lg">
                <CardHeader>
                  <CardTitle>Pending Review Items ({queue.length})</CardTitle>
                  <CardDescription>
                    High-risk or ungrounded flags requiring human decision
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <AnimatePresence>
                    <motion.div
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                      variants={{
                        hidden: { opacity: 0 },
                        visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
                        exit: { opacity: 0, transition: { staggerChildren: 0.04, staggerDirection: -1 } }
                      }}
                      className="space-y-3"
                    >
                      {queue.map((item: any) => (
                        <motion.div
                          key={item.clause_id}
                          variants={{
                            visible: { opacity: 1, y: 0, height: 'auto' },
                            hidden: { opacity: 0, y: 20 },
                            exit: { opacity: 0, y: -20, height: 0 }
                          }}
                          className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-2">
                                <Badge variant={item.risk_level}>{item.risk_level.toUpperCase()}</Badge>
                                <Badge variant={item.grounded ? 'success' : 'warning'}>
                                  {item.grounded ? 'Grounded' : 'Not Grounded'}
                                </Badge>
                              </div>
                              <p className="text-slate-300">{item.concern}</p>
                              <p className="text-xs text-slate-500 mt-1">Clause: <span className="font-mono">{item.clause_id.slice(0, 8)}...</span></p>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => setConfirmDialog({ flagId: item.clause_id, decision: 'accepted' })}
                                disabled={submitting === item.clause_id}
                              >
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  disabled={submitting === item.clause_id}
                                  loading={submitting === item.clause_id}
                                >
                                  Accept
                                </Button>
                              </motion.button>
                              <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => setConfirmDialog({ flagId: item.clause_id, decision: 'rejected' })}
                                disabled={submitting === item.clause_id}
                              >
                                <Button
                                  variant="danger"
                                  size="sm"
                                  disabled={submitting === item.clause_id}
                                  loading={submitting === item.clause_id}
                                >
                                  Reject
                                </Button>
                              </motion.button>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>
                  </AnimatePresence>
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
                  loading={!!submitting}
                >
                  {submitting ? 'Submitting...' : `Confirm ${confirmDialog?.decision}`}
                </Button>
              </div>
            </Modal>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}