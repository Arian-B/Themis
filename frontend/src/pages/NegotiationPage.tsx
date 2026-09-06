import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, AlertCircle, Send, MessageSquare, X } from 'lucide-react'
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
  const [formData, setFormData] = useState({
    clause_id: '',
    client_position: '',
  })
  const [showStartForm, setShowStartForm] = useState(!sessionId)

  const riskFlags = contractResults?.risk_flags || []
  const highRiskFlags = riskFlags.filter((f: any) => f.risk_level === 'critical' || f.risk_level === 'high' || !f.grounded)

  // Load transcript when sessionId is in URL
  useEffect(() => {
    if (sessionId) {
      loadTranscript()
    }
  }, [sessionId])

  const handleStartNegotiation = async () => {
    if (!formData.clause_id || !formData.client_position.trim()) return
    if (!currentContractId) {
      setError('No contract ID available')
      return
    }
    setStarting(true)
    setError(null)
    try {
      const response = await contractsApi.startNegotiation(
        currentContractId,
        formData.clause_id,
        formData.client_position
      )
      navigate(`/negotiate/${response.session_id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start negotiation')
    } finally {
      setStarting(false)
    }
  }

  const loadTranscript = async () => {
    if (!sessionId) return
    setLoading(true)
    try {
      const data = await contractsApi.getNegotiationTranscript(sessionId)
      setTranscript(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load transcript')
    } finally {
      setLoading(false)
    }
  }

  if (showStartForm) {
    return (
      <div className="min-h-screen bg-slate-950 py-8 px-4">
        <div className="max-w-2xl mx-auto space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-white">Start Negotiation</h1>
            <p className="text-slate-400 mt-1">Select a clause and describe your position</p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Negotiation Setup</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Select Clause to Negotiate
                </label>
                <div className="space-y-2">
                  {highRiskFlags.length === 0 ? (
                    <p className="text-slate-500">No high-risk flags available for negotiation</p>
                  ) : (
                    highRiskFlags.map((flag: any) => (
                      <label key={flag.clause_id} className="flex items-center gap-3 p-3 bg-slate-800/50 border border-slate-700 rounded-lg cursor-pointer hover:border-slate-600">
                        <input
                          type="radio"
                          name="negotiation-clause"
                          checked={formData.clause_id === flag.clause_id}
                          onChange={() => setFormData(prev => ({ ...prev, clause_id: flag.clause_id }))}
                          className="h-4 w-4 text-violet-600 border-slate-600 rounded focus:ring-violet-500"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-white truncate">{flag.concern.slice(0, 80)}...</p>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant={flag.risk_level} className="text-xs">{flag.risk_level}</Badge>
                            <Badge variant={flag.grounded ? 'success' : 'warning'} className="text-xs">
                              {flag.grounded ? 'Grounded' : 'Ungrounded'}
                            </Badge>
                          </div>
                        </div>
                      </label>
                    ))
                  )}
                </div>
              </div>

              <Textarea
                label="Your Position / Instructions"
                value={formData.client_position}
                onChange={(e) => setFormData(prev => ({ ...prev, client_position: e.target.value }))}
                placeholder="Describe your negotiation goals, acceptable compromises, red lines, etc."
                rows={4}
              />

              {error && (
                <div className="p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-300 text-sm flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <Button
                onClick={handleStartNegotiation}
                disabled={!formData.clause_id || !formData.client_position.trim() || starting}
                size="lg"
                className="w-full"
              >
                {starting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Starting Negotiation...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Start Negotiation
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {contractResults && (
            <Card>
              <CardHeader>
                <CardTitle>Contract Context</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-400">
                  Contract has {riskFlags.length} risk flags ({highRiskFlags.length} high-risk/ungrounded).
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    )
  }

  if (loading && !transcript) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 text-violet-500 animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading transcript...</p>
        </div>
      </div>
    )
  }

  if (error && !transcript) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Card className="max-w-md w-full mx-4">
          <CardContent className="text-center py-8">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Failed to load transcript</h2>
            <p className="text-slate-400 mb-6">{error}</p>
            <Button onClick={() => navigate('/contracts')}>Back to Contracts</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!transcript) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-400">No transcript found</p>
      </div>
    )
  }

  // Map backend outcome to display status
  const statusMap: Record<string, { label: string; variant: 'success' | 'critical' | 'warning' }> = {
    agreement_reached: { label: 'AGREED', variant: 'success' },
    impasse: { label: 'IMPASSE', variant: 'critical' },
    max_turns_reached: { label: 'MAX TURNS REACHED', variant: 'warning' },
  }
  const statusInfo = statusMap[transcript.final_status] || { label: transcript.final_status.toUpperCase(), variant: 'warning' }

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Negotiation Transcript</h1>
            <p className="text-slate-400 mt-1">Session: {sessionId?.slice(0, 8)}...</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={statusInfo.variant}>
              {statusInfo.label}
            </Badge>
            <Button variant="ghost" onClick={() => setShowStartForm(true)}>
              <X className="h-4 w-4 mr-1" />
              New Negotiation
            </Button>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Transcript ({transcript.redlines?.length || 0} turns)</CardTitle>
            <CardDescription>
              Proposer (our side) vs Counterparty (adversarial agent)
            </CardDescription>
          </CardHeader>
          <CardContent>
            {transcript.redlines?.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 text-slate-600" />
                <p>No turns recorded yet</p>
              </div>
            ) : (
              <div className="space-y-6">
                {transcript.redlines.map((turn: Redline) => (
                  <div
                    key={turn.id}
                    className={`p-4 rounded-lg border ${
                      turn.speaker === 'proposer'
                        ? 'border-blue-800 bg-blue-900/20'
                        : 'border-purple-800 bg-purple-900/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          turn.speaker === 'proposer'
                            ? 'bg-blue-900/50 text-blue-300'
                            : 'bg-purple-900/50 text-purple-300'
                        }`}>
                          {turn.speaker.toUpperCase()}
                        </span>
                        <Badge variant="low">Turn {turn.turn}</Badge>
                      </div>
                    </div>
                    <div className="prose prose-invert max-w-none text-sm">
                      <p className="text-slate-300 mb-2">{turn.proposed_text}</p>
                      <p className="text-slate-500 text-sm"><strong>Rationale:</strong> {turn.rationale}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Session Info</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <dt className="text-slate-400">Session ID</dt>
                <dd className="font-mono text-slate-300 break-all">{transcript.session_id}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Contract ID</dt>
                <dd className="font-mono text-slate-300 break-all">{transcript.contract_id}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Clauses</dt>
                <dd className="text-slate-300">{transcript.clause_ids?.join(', ') || 'N/A'}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Status</dt>
                <dd className="font-medium capitalize">{statusInfo.label}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Created</dt>
                <dd className="text-slate-300">{new Date(transcript.created_at).toLocaleString()}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}