import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
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
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-white mb-2">Upload Contract</h1>
          <p className="text-slate-400">
            Submit a contract for AI-powered risk analysis. Supported formats: PDF, TXT, DOC, DOCX
          </p>
        </div>

        <Card className="w-full">
          <CardHeader>
            <CardTitle>Contract Upload</CardTitle>
            <CardDescription>
              Drag and drop your contract file or click to browse
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              className={`
                border-2 border-dashed rounded-xl p-8 text-center transition-colors
                ${dragActive ? 'border-violet-500 bg-violet-500/10' : 'border-slate-700 hover:border-slate-600'}
                ${!isValidFile && file ? 'border-red-500 bg-red-500/10' : ''}
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
              <label htmlFor="contract-file" className="cursor-pointer">
                <FileText className="mx-auto h-12 w-12 text-slate-500 mb-4" />
                <p className="text-lg text-slate-300 mb-2">
                  {file ? file.name : 'Drop contract file here or click to browse'}
                </p>
                <p className="text-sm text-slate-500">
                  Max file size: 10MB • PDF, TXT, DOC, DOCX
                </p>
              </label>

              {file && !isValidFile && (
                <p className="mt-3 text-sm text-red-400 flex items-center justify-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  Unsupported file type. Please use PDF, TXT, DOC, or DOCX.
                </p>
              )}
            </div>

            {file && isValidFile && (
              <div className="mt-6 flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <div className="flex items-center gap-3">
                  <FileText className="h-6 w-6 text-violet-500" />
                  <div>
                    <p className="font-medium text-white">{file.name}</p>
                    <p className="text-sm text-slate-400">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              </div>
            )}

            {setUploadError && (
              <div className="mt-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-300 text-sm flex items-center gap-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {setUploadError}
              </div>
            )}

            <div className="mt-6 flex gap-3">
              <Button
                onClick={handleUpload}
                disabled={!file || !isValidFile || polling}
                size="lg"
                className="flex-1"
              >
                {polling ? (
                  <>
                    <Spinner size="sm" />
                    Uploading & Analyzing...
                  </>
                ) : (
                  'Upload & Analyze'
                )}
              </Button>
            </div>

            <div className="mt-6 pt-6 border-t border-slate-700">
              <h3 className="text-sm font-medium text-slate-400 mb-3">What happens next?</h3>
              <ol className="space-y-2 text-sm text-slate-500">
                <li className="flex items-center gap-2">
                  <Badge variant="violet">1</Badge>
                  File uploaded and text extracted
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="violet">2</Badge>
                  Jurisdiction detected & clauses extracted
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="violet">3</Badge>
                  Risk analysis with retrieval-grounded reasoning
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="violet">4</Badge>
                  Atomic verification of each claim
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="violet">5</Badge>
                  High-risk flags routed to review queue
                </li>
              </ol>
            </div>
          </CardContent>
        </Card>

        <div className="mt-8 text-center text-slate-500 text-sm">
          <p>Powered by Themis multi-agent legal intelligence pipeline</p>
        </div>
      </div>
    </div>
  )
}