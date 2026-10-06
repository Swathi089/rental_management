import AsyncStorage from '@react-native-async-storage/async-storage';

export type UserRole = 'OWNER' | 'TENANT' | 'ADMIN';

export type StoredSession = {
  accessToken: string | null;
  role: UserRole | null;
  name: string | null;
  userId: string | null;
};

export async function getAccessToken() {
  return AsyncStorage.getItem('access_token');
}

export async function getSession(): Promise<StoredSession> {
  const values = await AsyncStorage.getMany([
    'access_token', 'user_role', 'user_name', 'user_id',
  ]);

  return {
    accessToken: values.access_token,
    role: values.user_role as UserRole | null,
    name: values.user_name,
    userId: values.user_id,
  };
}

export async function saveSession(
  accessToken: string,
  user: { id: string; name: string; role: UserRole },
) {
  await AsyncStorage.setMany({
    access_token: accessToken,
    user_role: user.role,
    user_name: user.name,
    user_id: user.id,
  });
}

export async function clearSession() {
  await AsyncStorage.removeMany([
    'access_token',
    'user_role',
    'user_name',
    'user_id',
  ]);
}