import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';

import API from '@/api/api';
import { getSession, UserRole } from '@/api/auth';

type ScreenKind = 'properties' | 'tenants' | 'owner-rent' | 'tenant-property' | 'tenant-rent' | 'notifications';

type RecordItem = {
  [key: string]: unknown;
  notification_id?: string;
  rent_record_id?: string;
  title?: string;
  name?: string;
  property_title?: string;
  message?: string;
  status?: string;
  is_read?: boolean;
  amount_due?: number;
  amount_paid?: number;
  month?: number;
  year?: number;
  due_date?: string | null;
  created_at?: string;
};

const screenConfig: Record<ScreenKind, { title: string; endpoint: string; role: UserRole }> = {
  properties: { title: 'Properties', endpoint: '/properties/owner', role: 'OWNER' },
  tenants: { title: 'Tenants', endpoint: '/tenants/', role: 'OWNER' },
  'owner-rent': { title: 'Rent', endpoint: '/rent/owner', role: 'OWNER' },
  'tenant-property': { title: 'My property', endpoint: '/tenants/my-property', role: 'TENANT' },
  'tenant-rent': { title: 'Rent and payment history', endpoint: '/rent/my-rent', role: 'TENANT' },
  notifications: { title: 'Notifications', endpoint: '/notifications/', role: 'TENANT' },
};

function formatDate(value?: string | null) {
  if (!value) return 'Not set';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function amount(value?: number) {
  return value === undefined ? 'Not set' : `Rs. ${value.toLocaleString()}`;
}

export function ManagementScreen({ kind }: { kind: ScreenKind }) {
  const router = useRouter();
  const config = screenConfig[kind];
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [workingId, setWorkingId] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const session = await getSession();
        if (!session.accessToken || !session.role) {
          router.replace('/');
          return;
        }
        if (config.role !== 'TENANT' && session.role !== config.role) {
          router.replace(session.role === 'OWNER' ? '/owner' : '/tenant');
          return;
        }
        if (config.role === 'TENANT' && session.role !== 'TENANT' && kind !== 'notifications') {
          router.replace(session.role === 'OWNER' ? '/owner' : '/tenant');
          return;
        }

        const response = await API.get(config.endpoint);
        if (!active) return;
        const data = response.data;
        if (kind === 'tenant-property') {
          setRecords(data.property ? [data.property] : []);
        } else if (kind === 'notifications') {
          setRecords(data.notifications ?? []);
        } else {
          const key = kind === 'properties' ? 'properties' : kind === 'tenants' ? 'tenants' : 'rent_records';
          setRecords(data[key] ?? []);
        }
      } catch (loadError) {
        if (!active) return;
        const status = (loadError as { response?: { status?: number } }).response?.status;
        if (kind === 'tenant-property' && status === 404) {
          setRecords([]);
        } else {
          setMessage('Could not load this information. Check your connection and try again.');
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void load();
    return () => { active = false; };
  }, [config, kind, router]);

  async function markRead(record: RecordItem) {
    const id = record.notification_id;
    if (!id || workingId) return;
    setWorkingId(id);
    setMessage('');
    try {
      await API.put(`/notifications/${id}/read`);
      setRecords((current) => current.map((item) => item.notification_id === id ? { ...item, is_read: true } : item));
      setMessage('Notification marked as read.');
    } catch {
      setMessage('Could not update this notification.');
    } finally {
      setWorkingId('');
    }
  }

  async function payForTest(record: RecordItem) {
    const id = record.rent_record_id;
    if (!id || workingId) return;
    setWorkingId(id);
    setMessage('');
    try {
      await API.put(`/rent/${id}/pay`, { transaction_id: `TEST_${Date.now()}` });
      setRecords((current) => current.map((item) => item.rent_record_id === id
        ? { ...item, status: 'PAID', amount_paid: item.amount_due }
        : item));
      setMessage('Test payment recorded. No real payment was processed.');
    } catch (paymentError) {
      const detail = (paymentError as { response?: { data?: { message?: string } } }).response?.data?.message;
      setMessage(detail || 'Test payment could not be recorded.');
    } finally {
      setWorkingId('');
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.content}>
        <Text style={styles.heading}>{config.title}</Text>
        {loading ? <ActivityIndicator color="#256b55" style={styles.loader} /> : null}
        {message ? <Text accessibilityRole="alert" style={styles.message}>{message}</Text> : null}
        {!loading && records.length === 0 ? (
          <Text style={styles.empty}>{kind === 'tenant-property' ? 'No property is currently assigned to your account.' : 'Nothing to show yet.'}</Text>
        ) : null}
        {records.map((record, index) => {
          const key = record.notification_id ?? record.rent_record_id ?? String(record.property_id ?? record.tenant_id ?? index);
          const title = kind === 'properties' || kind === 'tenant-property'
            ? String(record.title ?? 'Property')
            : kind === 'tenants'
              ? String(record.name ?? 'Tenant')
              : kind.endsWith('rent')
                ? `${record.month ?? ''}/${record.year ?? ''}`
                : String(record.title ?? 'Notification');

          return (
            <View key={key} style={styles.row}>
              <View style={styles.rowHeader}>
                <Text style={styles.rowTitle}>{title}</Text>
                {kind === 'notifications' ? (
                  <Text style={[styles.badge, record.is_read ? styles.readBadge : styles.unreadBadge]}>
                    {record.is_read ? 'Read' : 'Unread'}
                  </Text>
                ) : kind.endsWith('rent') ? (
                  <Text style={[styles.badge, record.status === 'PAID' ? styles.readBadge : styles.unreadBadge]}>
                    {String(record.status ?? 'UNKNOWN')}
                  </Text>
                ) : null}
              </View>

              {kind === 'properties' || kind === 'tenant-property' ? (
                <>
                  <Text style={styles.detail}>{[record.address, record.city].filter(Boolean).join(', ')}</Text>
                  <Text style={styles.detail}>Rent: {amount(record.rent as number | undefined)}</Text>
                  <Text style={styles.detail}>Due day: {String(record.due_day ?? 'Not set')}</Text>
                  <Text style={styles.detail}>Status: {String(record.status ?? 'Not set')}</Text>
                </>
              ) : null}

              {kind === 'tenants' ? (
                <>
                  <Text style={styles.detail}>{String(record.email ?? '')}</Text>
                  <Text style={styles.detail}>Phone: {String(record.phone ?? 'Not set')}</Text>
                  <Text style={styles.detail}>Account: {record.is_activated ? 'Active' : 'Awaiting activation'}</Text>
                </>
              ) : null}

              {kind.endsWith('rent') ? (
                <>
                  <Text style={styles.detail}>{String(record.property_title ?? record.tenant_name ?? '')}</Text>
                  <Text style={styles.detail}>Due: {amount(record.amount_due)}</Text>
                  <Text style={styles.detail}>Due date: {formatDate(record.due_date)}</Text>
                  {record.transaction_id ? <Text style={styles.detail}>Transaction: {String(record.transaction_id)}</Text> : null}
                  {kind === 'tenant-rent' && record.status !== 'PAID' ? (
                    <Pressable style={styles.actionButton} disabled={workingId === record.rent_record_id} onPress={() => void payForTest(record)}>
                      <Text style={styles.actionText}>{workingId === record.rent_record_id ? 'Processing...' : 'Record test payment'}</Text>
                    </Pressable>
                  ) : null}
                </>
              ) : null}

              {kind === 'notifications' ? (
                <>
                  <Text style={styles.detail}>{String(record.message ?? '')}</Text>
                  <Text style={styles.detail}>{formatDate(record.created_at)}</Text>
                  {!record.is_read ? (
                    <Pressable style={styles.actionButton} disabled={workingId === record.notification_id} onPress={() => void markRead(record)}>
                      <Text style={styles.actionText}>{workingId === record.notification_id ? 'Updating...' : 'Mark as read'}</Text>
                    </Pressable>
                  ) : null}
                </>
              ) : null}
            </View>
          );
        })}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, backgroundColor: '#f5f6f3' },
  content: { width: '100%', maxWidth: 760, alignSelf: 'center' },
  heading: { color: '#18231e', fontSize: 26, fontWeight: '700', marginBottom: 18 },
  loader: { marginTop: 24 },
  empty: { color: '#66716b', fontSize: 15, paddingVertical: 20 },
  message: { color: '#256b55', fontSize: 14, marginBottom: 12 },
  row: { backgroundColor: '#ffffff', borderColor: '#e1e5df', borderWidth: 1, borderRadius: 6, padding: 16, marginBottom: 10 },
  rowHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', gap: 12, marginBottom: 8 },
  rowTitle: { color: '#18231e', flexShrink: 1, fontSize: 17, fontWeight: '700' },
  detail: { color: '#59645e', fontSize: 14, lineHeight: 21 },
  badge: { overflow: 'hidden', borderRadius: 4, fontSize: 11, fontWeight: '700', paddingHorizontal: 8, paddingVertical: 4 },
  readBadge: { backgroundColor: '#e3f0e9', color: '#256b55' },
  unreadBadge: { backgroundColor: '#f8e8d5', color: '#8a4f12' },
  actionButton: { alignSelf: 'flex-start', backgroundColor: '#256b55', borderRadius: 5, marginTop: 12, paddingHorizontal: 12, paddingVertical: 9 },
  actionText: { color: '#ffffff', fontSize: 13, fontWeight: '700' },
});