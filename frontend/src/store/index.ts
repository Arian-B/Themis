import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  jwt: string | null
  tenantId: string | null
  setAuth: (jwt: string, tenantId: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      jwt: null,
      tenantId: null,
      setAuth: (jwt: string, tenantId: string) => set({ jwt, tenantId }),
      clearAuth: () => set({ jwt: null, tenantId: null }),
    }),
    { name: 'themis-auth' }
  )
)

interface ContractState {
  currentContractId: string | null
  uploadStatus: 'idle' | 'uploading' | 'processing' | 'awaiting_review' | 'complete' | 'error'
  uploadError: string | null
  contractResults: any | null
  reviewQueue: any[] | null
  setCurrentContractId: (id: string | null) => void
  setUploadStatus: (status: ContractState['uploadStatus']) => void
  setUploadError: (error: string | null) => void
  setContractResults: (results: any | null) => void
  setReviewQueue: (queue: any[] | null) => void
  resetContract: () => void
}

export const useContractStore = create<ContractState>((set) => ({
  currentContractId: null,
  uploadStatus: 'idle',
  uploadError: null,
  contractResults: null,
  reviewQueue: null,
  setCurrentContractId: (id) => set({ currentContractId: id }),
  setUploadStatus: (status) => set({ uploadStatus: status }),
  setUploadError: (error) => set({ uploadError: error }),
  setContractResults: (results) => set({ contractResults: results }),
  setReviewQueue: (queue) => set({ reviewQueue: queue }),
  resetContract: () => set({
    currentContractId: null,
    uploadStatus: 'idle',
    uploadError: null,
    contractResults: null,
    reviewQueue: null,
  }),
}))

interface NegotiationState {
  currentSessionId: string | null
  transcript: any | null
  connectionStatus: 'idle' | 'connecting' | 'open' | 'closed' | 'error'
  setCurrentSessionId: (id: string | null) => void
  setTranscript: (transcript: any | null) => void
  setConnectionStatus: (status: NegotiationState['connectionStatus']) => void
  addRedline: (redline: any) => void
}

export const useNegotiationStore = create<NegotiationState>((set) => ({
  currentSessionId: null,
  transcript: null,
  connectionStatus: 'idle',
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  setTranscript: (transcript) => set({ transcript }),
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  addRedline: (redline) => set((state) => ({
    transcript: state.transcript
      ? { ...state.transcript, redlines: [...state.transcript.redlines, redline] }
      : { redlines: [redline] },
  })),
}))