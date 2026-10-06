
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';

import { clearSession, getSession } from '@/api/auth';
import API from '@/api/api';

type Property = {
  property_id: string;
  property_name?: string;
  rent?: number;
  status?: string;
};

type Tenant = {
  tenant_id?: string;
  id?: string;
  name?: string;
  email?: string;
};

type RentRecord = {
  rent_id?: string;
  amount_due?: number;
  amount_paid?: number;
  status?: string;
};

type Notification = {
  notification_id?: string;
  title?: string;
  message?: string;
  is_read?: boolean;
};

export default function OwnerScreen() {
  const router = useRouter();

  const [name, setName] = useState('');

  const [properties, setProperties] = useState<Property[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [rentRecords, setRentRecords] = useState<RentRecord[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      try {
        const session = await getSession();

        if (!session.accessToken || session.role !== 'OWNER') {
          router.replace('/');
          return;
        }

        if (active) {
          setName(session.name ?? 'Owner');
        }

        const [
  propertiesResponse,
  tenantsResponse,
  rentResponse,
  notificationsResponse,
] = await Promise.all([
  API.get('/properties/owner'),
  API.get('/tenants/'),
  API.get('/rent/owner'),
  API.get('/notifications/'),
]);



        if (!active) return;

        setProperties(propertiesResponse.data.properties ?? []);
        setTenants(tenantsResponse.data.tenants ?? []);
        setRentRecords(rentResponse.data.rent_records ?? []);
        setNotifications(notificationsResponse.data.notifications ?? []);
      } catch (error) {
        console.log('Dashboard loading error:', error);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadDashboard();

    return () => {
      active = false;
    };
  }, [router]);

  async function logout() {
    await clearSession();
    router.replace('/');
  }

  const pendingRent = rentRecords.filter(
    (record) => record.status === 'PENDING'
  ).length;

  const overdueRent = rentRecords.filter(
    (record) => record.status === 'OVERDUE'
  ).length;

  const unreadNotifications = notifications.filter(
    (notification) => !notification.is_read
  ).length;

  const sections = [
    {
      title: 'Properties',
      description: 'Review your rental properties',
      route: '/owner-properties' as const,
    },
    {
      title: 'Tenants',
      description: 'View tenants and account status',
      route: '/owner-tenants' as const,
    },
    {
      title: 'Rent',
      description: 'Review rent records and payment status',
      route: '/owner-rent' as const,
    },
    {
      title: 'Notifications',
      description: 'Payment updates and reminders',
      route: '/notifications' as const,
    },
  ];

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.content}>

        <View style={styles.header}>
          <View>
            <Text style={styles.eyebrow}>OWNER WORKSPACE</Text>
            <Text style={styles.title}>
              Welcome, {name || 'Owner'}
            </Text>
          </View>

          <Pressable
            accessibilityRole="button"
            onPress={() => void logout()}
            style={styles.logout}
          >
            <Text style={styles.logoutText}>Log out</Text>
          </Pressable>
        </View>

        <Text style={styles.subtitle}>
          Manage your properties, tenants, and rent in one place.
        </Text>

        {loading ? (
          <Text style={styles.loading}>Loading dashboard...</Text>
        ) : (
          <>
            <View style={styles.statsGrid}>

              <View style={styles.statCard}>
                <Text style={styles.statNumber}>
                  {properties.length}
                </Text>
                <Text style={styles.statLabel}>Properties</Text>
              </View>

              <View style={styles.statCard}>
                <Text style={styles.statNumber}>
                  {tenants.length}
                </Text>
                <Text style={styles.statLabel}>Tenants</Text>
              </View>

              <View style={styles.statCard}>
                <Text style={styles.statNumber}>
                  {pendingRent}
                </Text>
                <Text style={styles.statLabel}>Pending Rent</Text>
              </View>

              <View style={styles.statCard}>
                <Text style={styles.statNumber}>
                  {overdueRent}
                </Text>
                <Text style={styles.statLabel}>Overdue</Text>
              </View>

            </View>

            {unreadNotifications > 0 && (
              <Pressable
                onPress={() => router.push('/notifications')}
                style={styles.notificationBanner}
              >
                <Text style={styles.notificationTitle}>
                  {unreadNotifications} unread notification
                  {unreadNotifications > 1 ? 's' : ''}
                </Text>

                <Text style={styles.notificationText}>
                  Tap to view payment updates and reminders.
                </Text>
              </Pressable>
            )}
          </>
        )}

        <View style={styles.sections}>
          {sections.map((section) => (
            <Pressable
              key={section.title}
              onPress={() => router.push(section.route)}
              style={styles.section}
            >
              <Text style={styles.sectionTitle}>
                {section.title}
              </Text>

              <Text style={styles.sectionDescription}>
                {section.description}
              </Text>

              <Text style={styles.open}>Open</Text>
            </Pressable>
          ))}
        </View>

      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    padding: 20,
    backgroundColor: '#f5f6f3',
  },

  content: {
    width: '100%',
    maxWidth: 860,
    alignSelf: 'center',
  },

  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 16,
  },

  eyebrow: {
    color: '#256b55',
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 6,
  },

  title: {
    color: '#18231e',
    fontSize: 28,
    fontWeight: '700',
  },

  subtitle: {
    color: '#66716b',
    fontSize: 15,
    marginTop: 10,
    marginBottom: 22,
  },

  logout: {
    borderColor: '#cbd4ce',
    borderWidth: 1,
    borderRadius: 5,
    paddingHorizontal: 14,
    paddingVertical: 9,
  },

  logoutText: {
    color: '#35433b',
    fontSize: 14,
    fontWeight: '600',
  },

  loading: {
    color: '#66716b',
    fontSize: 15,
    marginBottom: 20,
  },

  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 16,
  },

  statCard: {
    backgroundColor: '#ffffff',
    borderColor: '#e1e5df',
    borderWidth: 1,
    borderRadius: 6,
    padding: 17,
    flexGrow: 1,
    flexBasis: '45%',
  },

  statNumber: {
    color: '#18231e',
    fontSize: 25,
    fontWeight: '700',
  },

  statLabel: {
    color: '#66716b',
    fontSize: 13,
    marginTop: 4,
  },

  notificationBanner: {
    backgroundColor: '#eef6f1',
    borderColor: '#cfe2d7',
    borderWidth: 1,
    borderRadius: 6,
    padding: 15,
    marginBottom: 16,
  },

  notificationTitle: {
    color: '#256b55',
    fontSize: 15,
    fontWeight: '700',
  },

  notificationText: {
    color: '#66716b',
    fontSize: 13,
    marginTop: 4,
  },

  sections: {
    gap: 10,
  },

  section: {
    backgroundColor: '#ffffff',
    borderColor: '#e1e5df',
    borderWidth: 1,
    borderRadius: 6,
    padding: 17,
  },

  sectionTitle: {
    color: '#18231e',
    fontSize: 18,
    fontWeight: '700',
  },

  sectionDescription: {
    color: '#66716b',
    fontSize: 14,
    marginTop: 4,
  },

  open: {
    color: '#256b55',
    fontSize: 13,
    fontWeight: '700',
    marginTop: 12,
  },
});

