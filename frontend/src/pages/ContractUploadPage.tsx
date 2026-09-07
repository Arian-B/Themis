import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, Loader2, CheckCircle, AlertCircle, Upload, ChevronDown } from 'lucide-react'
import { Button } from '../components/common/Button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/common/Card'
import { Input } from '../components/common/Input'
import { Spinner } from '../components/common/Spinner'
import { contractsApi } from '../services/api'
import { useContractStore } from '../store'
import { Badge } from '../components/common/Badge'

export function ContractUploadPage() {
  const navigate = useNavigate()
  const { setCurrentContractId, setUploadStatus, setUploadError } = useContractStore()
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [polling, setPolling] = useState(false)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0])
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploadStatus('uploading')
    setUploadError(null)

    try {
      const response = await contractsApi.upload(file)
      setCurrentContractId(response.contract_id)
      setUploadStatus('processing')
      setPolling(true)
      navigate(`/contracts/${response.contract_id}`)
    } catch (error: any) {
      setUploadStatus('error')
      setUploadError(error.response?.data?.detail || 'Upload failed. Please try again.')
    }
  }

  const getFileExtension = (filename: string) => {
    return filename.slice(((filename.lastIndexOf('.') - 1) >>> 0) + 2).toLowerCase()
  }

  const isValidFile = file ? ['pdf', 'txt', 'doc', 'docx'].includes(getFileExtension(file.name)) : false

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-slate-50 mb-3 tracking-tight">Upload Contract</h1>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            Submit a contract for AI-powered risk analysis. Supported formats: PDF, TXT, DOC, DOCX
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.4, 0, 0.2, 1] }}
        >
          <Card className="w-full" elevated padding="lg">
            <CardHeader>
              <CardTitle>Contract Upload</CardTitle>
              <CardDescription>
                Drag and drop your contract file or click to browse
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className={`
                  relative border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-300
                  ${dragActive
                    ? 'border-blue-500 bg-blue-500/5 bg-[radial-gradient(ellipse_at_center,_var(--color-brand-glow)_0%,_transparent_70%)]'
                    : 'border-slate-700 hover:border-slate-600'}
                  ${!isValidFile && file ? 'border-red-500 bg-red-500/5' : ''}
                `}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  id="contract-file"
                  accept=".pdf,.txt,.doc,.docx"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={polling}
                />
                <label htmlFor="contract-file" className="cursor-pointer flex flex-col items-center gap-4">
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="flex flex-col items-center gap-3 text-slate-400 group"
                  >
                    <div className="relative">
                      <Upload className="h-14 w-14 text-slate-500 group-hover:text-blue-400 transition-colors duration-300" />
                      {dragActive && (
                        <motion.span
                          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
                          transition={{ duration: 1, repeat: Infinity }}
                          className="absolute -top-2 -right-2 h-6 w-6 bg-blue-500 text-slate-50 rounded-full text-[10px] font-bold flex items-center justify-center"
                        >
                          +
                        </motion.span>
                      )}
                    </div>
                    <div className="text-left w-full max-w-xs">
                      <p className="text-lg font-medium text-slate-300 mb-1">
                        {file ? file.name : 'Drop contract file here or click to browse'}
                      </p>
                      <p className="text-sm text-slate-500">
                        Max file size: 10MB &bull; PDF, TXT, DOC, DOCX
                      </p>
                    </div>
                  </motion.div>
                </label>

                <input
                  type="file"
                  id="contract-file"
                  accept=".pdf,.txt,.doc,.docx"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={polling}
                />

                {file && !isValidFile && (
                  <motion.p
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 text-sm text-red-400 flex items-center justify-center gap-1.5"
                  >
                    <AlertCircle className="h-4 w-4 flex-shrink-0" />
                    Unsupported file type. Please use PDF, TXT, DOC, or DOCX.
                  </motion.p>
                )}
              </div>

              {file && isValidFile && (
                <motion.div
                  initial={{ opacity: 0, y: 10, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: 'auto' }}
                  exit={{ opacity: 0, y: -10, height: 0 }}
                  className="mt-6"
                >
                  <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-500/15 rounded-xl">
                        <FileText className="h-6 w-6 text-blue-400" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-50 truncate max-w-xs">{file.name}</p>
                        <p className="text-sm text-slate-400">
                          {(file.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => setFile(null)}
                      className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      aria-label="Remove file"
                    >
                      <ChevronDown className="h-5 w-5 rotate-180" />
                    </motion.button>
                  </div>
                </motion.div>
              )}

              {setUploadError && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center gap-2"
                >
                  <AlertCircle className="h-5 w-5 flex-shrink-0" />
                  {setUploadError}
                </motion.div>
              )}

              <div className="mt-8">
                <Button
                  onClick={handleUpload}
                  disabled={!file || !isValidFile || polling}
                  size="lg"
                  className="w-full"
                  loading={polling}
                >
                  {polling ? (
                    <>
                      <Spinner size="sm" />
                      Uploading & Analyzing...
                    </>
                  ) : (
                    <>
                      <Upload className="h-5 w-5" />
                      Upload & Analyze
                    </>
                  )}
                </Button>
              </div>

              <div className="mt-8 pt-6 border-t border-slate-800">
                <h3 className="text-sm font-medium text-slate-400 mb-4">What happens next?</h3>
                <ol className="space-y-3 text-sm text-slate-500">
                  {[
                    'File uploaded and text extracted',
                    'Jurisdiction detected & clauses extracted',
                    'Risk analysis with retrieval-grounded reasoning',
                    'Atomic verification of each claim',
                    'High-risk flags routed to review queue',
                  ].map((step, index) => (
                    <motion.li
                      key={step}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + index * 0.1, duration: 0.3 }}
                      className="flex items-center gap-3"
                    >
                      <Badge variant="info" size="sm">{index + 1}</Badge>
                      <span>{step}</span>
                    </motion.li>
                  ))}
                </ol>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <div className="mt-10 text-center text-slate-500 text-sm">
          <p>Powered by Themis multi-agent legal intelligence pipeline</p>
        </div>
      </div>
    </div>
  )
}