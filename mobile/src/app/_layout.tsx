import { Stack } from 'expo-router';

export default function RootLayout() {
  return (
    <Stack screenOptions={{ contentStyle: { backgroundColor: '#f5f6f3' } }}>
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="owner" options={{ title: 'Owner dashboard' }} />
      <Stack.Screen name="tenant" options={{ title: 'Tenant dashboard' }} />
      <Stack.Screen name="owner-properties" options={{ title: 'Properties' }} />
      <Stack.Screen name="owner-tenants" options={{ title: 'Tenants' }} />
      <Stack.Screen name="owner-rent" options={{ title: 'Rent' }} />
      <Stack.Screen name="tenant-property" options={{ title: 'My property' }} />
      <Stack.Screen name="tenant-rent" options={{ title: 'Rent and payment history' }} />
      <Stack.Screen name="notifications" options={{ title: 'Notifications' }} />
      <Stack.Screen name="explore" options={{ title: 'Explore' }} />
    </Stack>
  );
}
