import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import QuoteDetailModal from '../QuoteDetailModal'
import { ToastProvider } from '../../Toast'

const quote = {
  id: 42,
  quote_number: 'Q-0042',
  created_at: '2026-04-01T00:00:00Z',
  status: 'approved',
  expires_at: '2026-04-30T00:00:00Z',
  has_image: false,
  customer_name: 'Jane Doe',
  customer_email: 'jane@example.com',
  customer_notes: 'Please call before delivery',
  admin_notes: 'VIP account',
  subtotal: '120.00',
  total_price: '120.00',
  quantity: 1,
  unit_price: '120.00',
  lines: [],
}

const renderModal = () =>
  render(
    <ToastProvider>
      <QuoteDetailModal
        quote={quote}
        onClose={vi.fn()}
        onEdit={vi.fn()}
        onUpdateStatus={vi.fn()}
        onConvert={vi.fn()}
        onDownloadPDF={vi.fn()}
        onPrintPDF={vi.fn()}
        onDuplicate={vi.fn()}
        onCopyLink={vi.fn()}
        onDelete={vi.fn()}
        getStatusStyle={() => 'bg-blue-500/20 text-blue-400'}
      />
    </ToastProvider>
  )

describe('QuoteDetailModal replay privacy', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => quote,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('masks customer identity and note content only', async () => {
    renderModal()

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1))

    expect(screen.getByText('Customer').closest('[data-rum-mask="true"]')).toBeNull()
    expect(screen.getByText('Jane Doe').closest('[data-rum-mask="true"]')).toHaveAttribute('data-rum-mask', 'true')
    expect(screen.getByText('jane@example.com').closest('[data-rum-mask="true"]')).toHaveAttribute('data-rum-mask', 'true')

    const customerNote = screen.getByText(/Please call before delivery/, {
      selector: 'p',
    })
    const adminNote = screen.getByText(/VIP account/, {
      selector: 'p',
    })

    expect(customerNote.closest('[data-rum-mask="true"]')).toHaveAttribute('data-rum-mask', 'true')
    expect(adminNote.closest('[data-rum-mask="true"]')).toHaveAttribute('data-rum-mask', 'true')
    expect(screen.getByText('Product Details').closest('[data-rum-mask="true"]')).toBeNull()
  })
})
