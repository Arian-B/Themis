import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, AlertCircle, CheckCircle, Check, X, ArrowRight } from 'lucide-react'
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
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <Loader2 className="h-12 w-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Analyzing contract...</p>
          <p className="text-sm text-slate-500 mt-2">Polling status every 3s</p>
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
              <h2 className="text-xl font-semibold text-slate-50 mb-2">Failed to load results</h2>
              <p className="text-slate-400 mb-6">{error}</p>
              <Button onClick={() => navigate('/contracts')} iconLeft={<ArrowRight className="h-4 w-4 rotate-180" />}>
                Back to Upload
              </Button>
            </CardContent>
          </Card>
        </motion.div>
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
    <div className="min-h-screen bg-slate-950 py-8 px-4 md:py-12">
      <AnimatePresence mode="popLayout">
        <motion.div
          key={contractId}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
          className="max-w-6xl mx-auto space-y-6 px-4"
        >
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col md:flex-row md:items-center md:justify-between gap-4"
          >
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-slate-50">Contract Analysis</h1>
              <p className="text-slate-400 mt-1">Contract ID: <span className="font-mono text-slate-300">{contractId?.slice(0, 8)}...</span></p>
            </div>
            <Button
              onClick={() => navigate(`/contracts/${contractId}/review`)}
              disabled={!risk_flags?.length}
              iconRight={<ArrowRight className="h-4 w-4" />}
            >
              Review Queue ({risk_flags?.filter((f: any) => f.risk_level === 'critical' || f.risk_level === 'high' || !f.grounded).length || 0})
            </Button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            layout
          >
            <Card elevated padding="lg">
              <CardHeader>
                <CardTitle>Jurisdiction</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                    <p className="text-sm text-slate-400 mb-1">Country</p>
                    <p className="text-xl font-medium text-slate-50">{jurisdiction?.country || 'Unknown'}</p>
                  </div>
                  <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                    <p className="text-sm text-slate-400 mb-1">Region</p>
                    <p className="text-xl font-medium text-slate-50">{jurisdiction?.region || 'N/A'}</p>
                  </div>
                  <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                    <p className="text-sm text-slate-400 mb-1">Confidence</p>
                    <div className="flex items-center gap-3">
                      <p className="text-2xl font-bold text-slate-50">{(jurisdiction?.confidence * 100).toFixed(0)}%</p>
                      <motion.div
                        className="h-2 flex-1 bg-slate-800 rounded-full overflow-hidden"
                        initial={{ width: 0 }}
                        animate={{ width: `${jurisdiction?.confidence * 100}%` }}
                        transition={{ delay: 0.3, duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
                      >
                        <motion.div
                          className="h-full bg-gradient-to-r from-blue-500 to-blue-400"
                          initial={{ width: 0 }}
                          animate={{ width: '100%' }}
                          transition={{ delay: 0.3, duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
                        />
                      </motion.div>
                    </div>
                  </div>
                </div>
                {jurisdiction?.reasoning && (
                  <motion.p
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="mt-5 text-sm text-slate-400 p-4 bg-slate-800/50 rounded-xl border border-slate-700"
                  >
                    {jurisdiction.reasoning}
                  </motion.p>
                )}
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            layout
          >
            <Card elevated padding="lg">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Extracted Clauses ({clauses?.length || 0})</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {clauses?.length === 0 ? (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-slate-500 text-center py-8"
                  >
                    No clauses extracted
                  </motion.p>
                ) : (
                  <AnimatePresence>
                    <motion.div
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                      variants={{
                        hidden: { opacity: 0 },
                        visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
                        exit: { opacity: 0, transition: { staggerChildren: 0.03, staggerDirection: -1 } }
                      }}
                      className="space-y-3 max-h-[600px] overflow-y-auto pr-2"
                    >
                      {clauses.map((clause: any) => (
                        <motion.div
                          key={clause.id}
                          variants={{
                            visible: { opacity: 1, y: 0 },
                            hidden: { opacity: 0, y: 20 },
                            exit: { opacity: 0, y: -20, height: 0 }
                          }}
                          className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-medium text-slate-50">{clause.title || 'Untitled'}</span>
                                <Badge variant="low">{clause.clause_type}</Badge>
                              </div>
                              <p className="text-sm text-slate-400 line-clamp-2">{clause.text}</p>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>
                  </AnimatePresence>
                )}
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            layout
          >
            <Card elevated padding="lg">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Risk Flags ({risk_flags?.length || 0})</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <AnimatePresence>
                  {risk_flags?.length === 0 ? (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      className="text-center py-12"
                    >
                      <CheckCircle className="h-16 w-16 text-emerald-500 mx-auto mb-4" />
                      <p className="text-slate-400">No risk flags detected</p>
                    </motion.div>
                  ) : (
                    <motion.div
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                      variants={{
                        hidden: { opacity: 0 },
                        visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
                        exit: { opacity: 0, transition: { staggerChildren: 0.04, staggerDirection: -1 } }
                      }}
                      className="space-y-4"
                    >
                      {risk_flags.map((flag: any) => (
                        <motion.div
                          key={flag.clause_id}
                          variants={{
                            visible: { opacity: 1, y: 0 },
                            hidden: { opacity: 0, y: 20 },
                            exit: { opacity: 0, y: -20, height: 0 }
                          }}
                          className="p-5 bg-slate-800/50 border border-slate-700 rounded-xl hover:border-slate-600 transition-colors duration-200"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-3">
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
                              <p className="text-slate-300 mb-3 leading-relaxed">{flag.concern}</p>
                              {flag.suggested_redline && (
                                <motion.p
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: 'auto' }}
                                  className="text-sm text-slate-400 p-3 bg-slate-800/50 rounded-lg border border-slate-700"
                                >
                                  <span className="font-medium text-slate-300">Suggested redline:</span> {flag.suggested_redline}
                                </motion.p>
                              )}
                              {flag.citation_ids?.length && (
                                <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                                  <span className="font-mono">Citations:</span>
                                  <span>{flag.citation_ids.join(', ')}</span>
                                </p>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}