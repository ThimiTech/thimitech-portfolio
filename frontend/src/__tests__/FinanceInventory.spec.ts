import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import RecordActions from '../components/app/finance/RecordActions.vue'
import AssignmentDialog from '../components/app/inventory/AssignmentDialog.vue'
import api from '../api/api'
import { confirmDialog } from '../components/app/ui/confirm'
import { type Asset } from '../components/app/inventory/inventory'

vi.mock('../api/api', () => ({ default: { post: vi.fn<() => Promise<unknown>>() } }))
vi.mock('../components/app/ui/confirm', () => ({ confirmDialog: vi.fn<() => Promise<boolean>>().mockResolvedValue(true) }))
const modalStub = { props: ['open'], template: '<div v-if="open"><slot /></div>' }
beforeEach(() => {
  vi.mocked(api.post).mockReset()
})
afterEach(() => {
  vi.clearAllMocks()
})

describe('Finance lifecycle controls', () => {
  it('records an existing payment reference using the correct resource endpoint', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: {} })
    const wrapper = mount(RecordActions, {
      props: { resource: 'payslips', id: 12, status: 'issued' },
      global: { stubs: { Modal: modalStub } },
    })
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Record payment')!
      .trigger('click')
    await wrapper.get('textarea').setValue('BANK-REFERENCE-12')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('finance/payslips/12/mark-paid/', {
      payment_reference: 'BANK-REFERENCE-12',
    })
    expect(wrapper.emitted('changed')).toHaveLength(1)
    wrapper.unmount()
  })

  it('keeps a failed issue action visible for retry', async () => {
    vi.mocked(confirmDialog).mockResolvedValue(true)
    vi.mocked(api.post).mockRejectedValue(new Error('offline'))
    const wrapper = mount(RecordActions, {
      props: { resource: 'invoices', id: 5, status: 'draft' },
      global: { stubs: { Modal: modalStub } },
    })
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Mark issued')!
      .trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('try again')
    expect(wrapper.emitted('changed')).toBeUndefined()
    expect(wrapper.text()).toContain('Mark issued')
    wrapper.unmount()
  })

  it('offers no monetary transitions for paid or void records', () => {
    for (const status of ['paid', 'void']) {
      const wrapper = mount(RecordActions, {
        props: { resource: 'invoices', id: 5, status },
        global: { stubs: { Modal: modalStub } },
      })
      expect(wrapper.findAll('button')).toHaveLength(0)
      wrapper.unmount()
    }
  })
})

describe('Asset returns', () => {
  it('sends a return condition while preserving the assignment identity', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: {} })
    const asset: Asset = {
      id: 1,
      tag: 'TT-1',
      name: 'Receiver',
      category: 1,
      category_name: 'Survey',
      serial_number: '',
      location: '',
      purchase_date: null,
      purchase_cost: null,
      currency: 'NPR',
      status: 'assigned',
      notes: '',
      assigned_to: { assignment: 9, id: 2, name: 'Staff member', due_back: null },
    }
    const wrapper = mount(AssignmentDialog, {
      props: { asset, staff: [], mode: 'return' },
      global: { stubs: { Modal: modalStub } },
    })
    await wrapper.get('select').setValue('maintenance')
    await wrapper.get('textarea').setValue('Inspect antenna before reuse.')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('inventory/assignments/9/return/', {
      condition: 'maintenance',
      return_note: 'Inspect antenna before reuse.',
    })
    expect(wrapper.emitted('saved')).toHaveLength(1)
    expect(wrapper.emitted('close')).toHaveLength(1)
    wrapper.unmount()
  })
})
