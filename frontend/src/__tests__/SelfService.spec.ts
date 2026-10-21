import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CorrectionsPanel from '../components/app/attendance/CorrectionsPanel.vue'
import { navFor } from '../components/app/nav'
import api from '../api/api'
import type { Correction } from '../components/app/attendance/attendance'

vi.mock('../api/api', () => ({
  default: { get: vi.fn<() => Promise<unknown>>(), post: vi.fn<() => Promise<unknown>>() },
}))
const modalStub = { props: ['open'], template: '<div v-if="open"><slot /></div>' }
const pending: Correction = {
  id: 7, user: 3, user_name: 'Maya', date: '2026-10-01', check_in: '09:30:00', check_out: null, reason: 'Missed punch',
  status: 'pending', approver: null, approver_name: null, decision_note: '', decided_at: null, created_at: '', can_decide: true,
}
afterEach(() => vi.clearAllMocks())

function mountPanel(canApprove: boolean) {
  vi.mocked(api.get).mockImplementation((_url, cfg) =>
    Promise.resolve({ data: (cfg?.params as { scope?: string } | undefined)?.scope === 'approvals' ? [pending] : [] }),
  )
  return mount(CorrectionsPanel, { props: { canApprove }, global: { stubs: { Modal: modalStub } } })
}

describe('Attendance corrections', () => {
  it('only loads the approvals queue for approvers', async () => {
    mountPanel(false)
    await flushPromises()
    expect(api.get).toHaveBeenCalledTimes(1)
    expect(api.get).toHaveBeenCalledWith('attendance/corrections/')
  })

  it('requires a note to reject, then posts the decision', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: {} })
    const w = mountPanel(true)
    await flushPromises()
    const reject = () => w.findAll('button').find((b) => b.text() === 'Reject')!.trigger('click')
    await reject()
    expect(api.post).not.toHaveBeenCalled()
    expect(w.text()).toContain('Add a note')
    await w.get('textarea').setValue('Badge log says 11:00')
    await reject()
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('attendance/corrections/7/reject/', { decision_note: 'Badge log says 11:00' })
    expect(w.emitted('decided')).toHaveLength(1)
    expect(w.text()).not.toContain('Missed punch')
  })

  it('sends an empty check-out as null', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { ...pending, id: 8, user_name: 'Me' } })
    const w = mountPanel(false)
    await flushPromises()
    await w.findAll('button').find((b) => b.text().includes('Request a correction'))!.trigger('click')
    await w.get('input[type="time"]').setValue('09:30')
    await w.get('form textarea').setValue('Forgot')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(vi.mocked(api.post).mock.calls[0]![1]).toMatchObject({ check_in: '09:30', check_out: null, reason: 'Forgot' })
  })
})

describe('Self-service navigation', () => {
  it('shows My pay and My assets to every employee', () => {
    const labels = navFor((r) => r === 'employee').flatMap((g) => g.items.map((i) => i.label))
    expect(labels).toEqual(expect.arrayContaining(['My pay', 'My assets']))
    expect(labels).not.toContain('Finance')
  })
})
