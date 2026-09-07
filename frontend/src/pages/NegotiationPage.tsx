import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, AlertCircle, Send, MessageSquare, X, ArrowLeft, ArrowRight, CheckCircle } from 'lucide-react'
import { Button } from '../components/common/Button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { Textarea } from '../components/common/Textarea'
import { contractsApi } from '../services/api'
import { useContractStore } from '../store'

interface Redline {
  id: string
  turn: number
  speaker: 'proposer' | 'counterparty'
  proposed_text: string
  rationale: string
  diff_additions: string[]
  diff_deletions: string[]
  agreed: boolean
  impasse: boolean
}

interface NegotiationTranscript {
  session_id: string
  contract_id: string
  clause_ids: string[]
  redlines: Redline[]
  final_status: 'agreement_reached' | 'impasse' | 'max_turns_reached'
  created_at: string
}

export function NegotiationPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const { contractResults, currentContractId } = useContractStore()
  const [transcript, setTranscript] = useState<NegotiationTranscript | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [formData, setFormData] = useState({ clause_id: '', client_position: '' })
  const [showStartForm, setShowStartForm] = useState(!sessionId)

  const riskFlags = contractResults?.risk_flags || []
  const highRiskFlags = riskFlags.filter((f: any) => f.risk_level === 'critical' || f.risk_level === 'high' || !f.grounded)

  useEffect(() => { if (sessionId) loadTranscript() }, [sessionId])

  const handleStartNegotiation = async () => {
    if (!formData.clause_id || !formData.client_position.trim() || !currentContractId) return
    setStarting(true); setError(null)
    try {
      const res = await contractsApi.startNegotiation(currentContractId, formData.clause_id, formData.client_position)
      navigate(`/negotiate/${res.session_id}`)
    } catch (e: any) { setError(e.response?.data?.detail || 'Failed to start negotiation') }
    finally { setStarting(false) }
  }

  const loadTranscript = async () => {
    if (!sessionId) return
    setLoading(true)
    try { setTranscript(await contractsApi.getNegotiationTranscript(sessionId)) }
    catch (e: any) { setError(e.response?.data?.detail || 'Failed to load transcript') }
    finally { setLoading(false) }
  }

  /* ────────────────────────── START FORM ────────────────────────── */
  if (showStartForm) {
    return (
      <div className="min-h-screen bg-slate-950 py-8 px-4 md:py-12">
        <AnimatePresence mode="popLayout">
          <motion.div
            key="start-form"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
            className="max-w-2xl mx-auto space-y-6 px-4"
          >
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="mb-8">
              <h1 className="text-3xl md:text-4xl font-bold text-slate-50">Start Negotiation</h1>
              <p className="text-slate-400 mt-1">Select a clause and describe your position</p>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card elevated padding="lg">
                <CardHeader><CardTitle>Negotiation Setup</CardTitle></CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-3">Select Clause to Negotiate</label>
                    <AnimatePresence>
                      {highRiskFlags.length === 0 ? (
                        <motion.div initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="text-slate-500 text-center py-8">
                          No high-risk flags available for negotiation
                        </motion.div>
                      ) : (
                        <motion.div
                          initial="hidden" animate="visible" exit="exit"
                          variants={{ hidden:{opacity:0}, visible:{opacity:1, transition:{staggerChildren:0.05}}, exit:{opacity:0, transition:{staggerChildren:0.03, staggerDirection:-1}} }}
                          className="space-y-2"
                        >
                          {highRiskFlags.map((flag: any) => (
                            <motion.label key={flag.clause_id}
                              variants={{ visible:{opacity:1,x:0}, hidden:{opacity:0,x:-20}, exit:{opacity:0,x:-20} }}
                              className="flex items-center gap-3 p-3 bg-slate-800/50 border border-slate-700 rounded-xl cursor-pointer hover:border-blue-500/50 transition-colors"
                            >
                              <input type="radio" name="negotiation-clause" checked={formData.clause_id===flag.clause_id}
                                onChange={()=>setFormData(p=>({...p,clause_id:flag.clause_id}))}
                                className="h-4 w-4 text-blue-600 border-slate-600 rounded focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-950" />
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-slate-50 truncate">{flag.concern.slice(0,100)}...</p>
                                <div className="flex items-center gap-2 mt-1">
                                  <Badge variant={flag.risk_level} className="text-xs">{flag.risk_level}</Badge>
                                  <Badge variant={flag.grounded?'success':'warning'} className="text-xs">{flag.grounded?'Grounded':'Ungrounded'}</Badge>
                                </div>
                              </div>
                            </motion.label>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} transition={{delay:0.1}}>
                    <Textarea label="Your Position / Instructions" value={formData.client_position}
                      onChange={e=>setFormData(p=>({...p,client_position:e.target.value}))}
                      placeholder="Describe your negotiation goals, acceptable compromises, red lines, etc." rows={4} />
                  </motion.div>

                  {error && (
                    <motion.div initial={{opacity:0,y:10}} animate={{opacity:1,y:0}}
                      className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 flex-shrink-0" /> {error}
                    </motion.div>
                  )}

                  <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} transition={{delay:0.15}}>
                    <Button onClick={handleStartNegotiation} disabled={!formData.clause_id||!formData.client_position.trim()||starting}
                      size="lg" className="w-full" loading={starting}>
                      {starting ? (<><Loader2 className="h-5 w-5 animate-spin"/> Starting Negotiation...</>) : (<><Send className="h-5 w-5"/> Start Negotiation</>)}
                    </Button>
                  </motion.div>
                </CardContent>
              </Card>
            </motion.div>

            {contractResults && (
              <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} transition={{delay:0.2}}>
                <Card elevated padding="md">
                  <CardHeader><CardTitle>Contract Context</CardTitle></CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-400">Contract has {riskFlags.length} risk flags ({highRiskFlags.length} high-risk/ungrounded).</p>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    )
  }

  /* ────────────────────────── LOADING / ERROR / EMPTY ────────────────────────── */
  if (loading && !transcript) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <motion.div initial={{opacity:0,scale:0.9}} animate={{opacity:1,scale:1}} className="text-center">
          <Loader2 className="h-12 w-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading transcript...</p>
        </motion.div>
      </div>
    )
  }
  if (error && !transcript) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}}>
          <Card className="max-w-md w-full mx-4 elevated" padding="lg">
            <CardContent className="text-center py-4">
              <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-slate-50 mb-2">Failed to load transcript</h2>
              <p className="text-slate-400 mb-6">{error}</p>
              <Button onClick={()=>navigate('/contracts')} iconLeft={<ArrowLeft className="h-4 w-4" />}>Back to Contracts</Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    )
  }
  if (!transcript) {
    return <div className="min-h-screen bg-slate-950 flex items-center justify-center"><p className="text-slate-400">No transcript found</p></div>
  }

  /* ────────────────────────── TRANSCRIPT VIEW ────────────────────────── */
  const statusMap = { agreement_reached:{label:'AGREED',variant:'success'}, impasse:{label:'IMPASSE',variant:'critical'}, max_turns_reached:{label:'MAX TURNS REACHED',variant:'warning'} }
  const statusInfo = statusMap[transcript.final_status] || {label:transcript.final_status.toUpperCase(),variant:'warning'}

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4 md:py-12">
      <AnimatePresence mode="popLayout">
        <motion.div key={sessionId} initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-20}} transition={{duration:0.4,ease:[0.4,0,0.2,1]}} className="max-w-5xl mx-auto space-y-6 px-4">
          <motion.div initial={{opacity:0,y:-10}} animate={{opacity:1,y:0}} transition={{duration:0.4}} className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div><h1 className="text-3xl md:text-4xl font-bold text-slate-50">Negotiation Transcript</h1>
              <p className="text-slate-400 mt-1">Session: <span className="font-mono text-slate-300">{sessionId?.slice(0,8)}...</span></p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
              <Button variant="ghost" onClick={()=>setShowStartForm(true)} iconLeft={<ArrowLeft className="h-4 w-4" />}>New Negotiation</Button>
            </div>
          </motion.div>

          <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} transition={{delay:0.1}} layout>
            <Card elevated padding="lg">
              <CardHeader>
                <CardTitle>Transcript ({transcript.redlines?.length||0} turns)</CardTitle>
                <CardDescription>Proposer (our side) vs Counterparty (adversarial agent)</CardDescription>
              </CardHeader>
              <CardContent>
                <AnimatePresence>
                  {transcript.redlines?.length===0 ? (
                    <motion.div initial={{opacity:0,scale:0.9}} animate={{opacity:1,scale:1}} exit={{opacity:0,scale:0.9}} className="text-center py-12">
                      <MessageSquare className="h-16 w-16 mx-auto mb-4 text-slate-600" />
                      <p className="text-slate-500">No turns recorded yet</p>
                    </motion.div>
                  ) : (
                    <motion.div
                      initial="hidden" animate="visible" exit="exit"
                      variants={{hidden:{opacity:0}, visible:{opacity:1,transition:{staggerChildren:0.12}}, exit:{opacity:0,transition:{staggerChildren:0.06,staggerDirection:-1}}}}
                      className="space-y-5"
                    >
                      {transcript.redlines.map((turn:Redline)=>(
                        <motion.div key={turn.id}
                          variants={{visible:{opacity:1,x:turn.speaker==='proposer'?-30:30}, hidden:{opacity:0,x:turn.speaker==='proposer'?-50:50}, exit:{opacity:0,x:turn.speaker==='proposer'?-50:50}}}
                          layout className={`relative p-5 rounded-2xl ${turn.speaker==='proposer'?'bg-blue-500/5 border border-blue-500/20':'bg-purple-500/5 border border-purple-500/20'} ${turn.agreed?'border-emerald-500/50':''} ${turn.impasse?'border-red-500/50':''}`}
                        >
                          <div className="absolute top-4 right-4"><Badge variant="low">Turn {turn.turn}</Badge></div>
                          <div className="flex items-center gap-3 mb-4">
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${turn.speaker==='proposer'?'bg-blue-500/20 text-blue-400 border border-blue-500/30':'bg-purple-500/20 text-purple-400 border border-purple-500/30'}`}>
                              {turn.speaker==='proposer'?'PROPOSER':'COUNTERPARTY'}
                            </span>
                            {turn.agreed && <Badge variant="success" size="sm">AGREED</Badge>}
                            {turn.impasse && <Badge variant="critical" size="sm">IMPASSE</Badge>}
                          </div>
                          <div className="prose prose-invert max-w-none text-sm">
                            <p className="text-slate-300 mb-3 whitespace-pre-wrap">{turn.proposed_text}</p>
                            <p className="text-slate-500 text-sm"><strong>Rationale:</strong> {turn.rationale}</p>
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} transition={{delay:0.15}} layout>
            <Card elevated padding="lg">
              <CardHeader><CardTitle>Session Info</CardTitle></CardHeader>
              <CardContent>
                <dl className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700"><dt className="text-slate-400 mb-1">Session ID</dt><dd className="font-mono text-slate-300 break-all">{transcript.session_id}</dd></div>
                  <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700"><dt className="text-slate-400 mb-1">Contract ID</dt><dd className="font-mono text-slate-300 break-all">{transcript.contract_id}</dd></div>
                  <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700"><dt className="text-slate-400 mb-1">Clauses</dt><dd className="text-slate-300">{transcript.clause_ids?.join(', ')||'N/A'}</dd></div>
                  <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700 md:col-span-3">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div><dt className="text-slate-400 mb-1">Status</dt><dd className="font-medium text-slate-50 capitalize">{statusInfo.label}</dd></div>
                      <div><dt className="text-slate-400 mb-1">Created</dt><dd className="text-slate-300">{new Date(transcript.created_at).toLocaleString()}</dd></div>
                    </div>
                  </div>
                </dl>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}