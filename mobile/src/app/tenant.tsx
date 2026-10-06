import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';

import API from '@/api/api';
import { clearSession, getSession } from '@/api/auth';

type TenantProperty = { title?: string; address?: string; city?: string; rent?: number; due_day?: number };
type RentRecord = { rent_record_id: string; month: number; year: number; amount_due: number; status: string; due_date: string | null };

export default function TenantScreen() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [property, setProperty] = useState<TenantProperty | null>(null);
  const [rentRecords, setRentRecords] = useState<RentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    let active = true;
    async function loadDashboard() {
      const session = await getSession();
      if (!active) return;
      if (!session.accessToken || session.role !== 'TENANT') {
        router.replace('/');
        return;
      }
      setName(session.name ?? 'Tenant');
      const [propertyResult, rentResult] = await Promise.allSettled([
        API.get('/tenants/my-property'),
        API.get('/rent/my-rent'),
      ]);
      if (!active) return;
      if (propertyResult.status === 'fulfilled') {
        setProperty(propertyResult.value.data.property ?? null);
      }
      if (rentResult.status === 'fulfilled') {
        setRentRecords(rentResult.value.data.rent_records ?? []);
      }
      if (propertyResult.status === 'rejected' && rentResult.status === 'rejected') {
        setLoadError('Could not load your rental details. Check your connection and try again.');
      }
      setLoading(false);
    }
    void loadDashboard();
    return () => { active = false; };
  }, [router]);

  async function logout() {
    await clearSession();
    router.replace('/');
  }

  const currentRent = rentRecords.find((record) => record.status !== 'PAID') ?? rentRecords[0];

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.content}>
        <View style={styles.header}>
          <View>
            <Text style={styles.eyebrow}>TENANT ACCOUNT</Text>
            <Text style={styles.title}>Hello, {name || 'Tenant'}</Text>
          </View>
          <Pressable accessibilityRole="button" onPress={() => void logout()} style={styles.logout}>
            <Text style={styles.logoutText}>Log out</Text>
          </Pressable>
        </View>
        {loading ? <ActivityIndicator color="#256b55" style={styles.loader} /> : null}
        {loadError ? <Text accessibilityRole="alert" style={styles.error}>{loadError}</Text> : null}

        <View style={styles.summary}>
          <Text style={styles.summaryLabel}>MY PROPERTY</Text>
          <Text style={styles.propertyTitle}>{property?.title ?? 'No property assigned'}</Text>
          <Text style={styles.detail}>{[property?.address, property?.city].filter(Boolean).join(', ')}</Text>
          <View style={styles.metrics}>
            <View style={styles.metric}>
              <Text style={styles.metricLabel}>CURRENT RENT</Text>
              <Text style={styles.metricValue}>{currentRent ? `Rs. ${currentRent.amount_due.toLocaleString()}` : property?.rent ? `Rs. ${property.rent.toLocaleString()}` : 'Not set'}</Text>
            </View>
            <View style={styles.metric}>
              <Text style={styles.metricLabel}>DUE DATE</Text>
              <Text style={styles.metricValue}>{currentRent?.due_date ? new Date(currentRent.due_date).toLocaleDateString() : property?.due_day ? `Day ${property.due_day} each month` : 'Not set'}</Text>
            </View>
          </View>
        </View>

        <View style={styles.actions}>
          <Action title="My Property" description="View your assigned rental" onPress={() => router.push('/tenant-property')} />
          <Action title="Payment History" description="View monthly rent records" onPress={() => router.push('/tenant-rent')} />
          <Action title="Pay Rent" description="Use the existing test payment flow" onPress={() => router.push('/tenant-rent')} />
          <Action title="Notifications" description="Rent reminders and updates" onPress={() => router.push('/notifications')} />
        </View>
      </View>
    </ScrollView>
  );
}

function Action({ title, description, onPress }: { title: string; description: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={styles.action}>
      <Text style={styles.actionTitle}>{title}</Text>
      <Text style={styles.actionDescription}>{description}</Text>
      <Text style={styles.open}>Open</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  page: { flexGrow: 1, padding: 20, backgroundColor: '#f5f6f3' },
  content: { width: '100%', maxWidth: 860, alignSelf: 'center' },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', gap: 16, marginBottom: 18 },
  eyebrow: { color: '#256b55', fontSize: 11, fontWeight: '700', marginBottom: 6 },
  title: { color: '#18231e', fontSize: 27, fontWeight: '700' },
  logout: { borderColor: '#cbd4ce', borderWidth: 1, borderRadius: 5, paddingHorizontal: 14, paddingVertical: 9 },
  logoutText: { color: '#35433b', fontSize: 14, fontWeight: '600' },
  loader: { marginVertical: 18 },
  error: { color: '#a3312d', fontSize: 14, marginBottom: 12 },
  summary: { backgroundColor: '#ffffff', borderColor: '#e1e5df', borderWidth: 1, borderRadius: 6, padding: 18, marginBottom: 14 },
  summaryLabel: { color: '#256b55', fontSize: 11, fontWeight: '700' },
  propertyTitle: { color: '#18231e', fontSize: 21, fontWeight: '700', marginTop: 8 },
  detail: { color: '#66716b', fontSize: 14, marginTop: 4 },
  metrics: { flexDirection: 'row', gap: 16, marginTop: 18 },
  metric: { flex: 1, minWidth: 120 },
  metricLabel: { color: '#66716b', fontSize: 11, fontWeight: '700' },
  metricValue: { color: '#18231e', fontSize: 17, fontWeight: '700', marginTop: 4 },
  actions: { gap: 10 },
  action: { backgroundColor: '#ffffff', borderColor: '#e1e5df', borderWidth: 1, borderRadius: 6, padding: 16 },
  actionTitle: { color: '#18231e', fontSize: 17, fontWeight: '700' },
  actionDescription: { color: '#66716b', fontSize: 14, marginTop: 4 },
  open: { color: '#256b55', fontSize: 13, fontWeight: '700', marginTop: 11 },
});