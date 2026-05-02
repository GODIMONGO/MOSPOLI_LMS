<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="logo">
        <h1>Регистрация</h1>
      </div>
      
      <form @submit.prevent="handleRegister">
        <md-outlined-text-field
          v-model="name"
          type="text"
          label="Имя"
          placeholder="Введите ваше имя"
        ></md-outlined-text-field>
        
        <md-outlined-text-field
          v-model="email"
          type="email"
          label="Email"
          placeholder="Введите ваш email"
        ></md-outlined-text-field>
        
        <md-outlined-text-field
          v-model="password"
          type="password"
          label="Пароль"
          placeholder="Придумайте пароль"
          minlength="6"
        ></md-outlined-text-field>
        
        <md-outlined-text-field
          v-model="confirmPassword"
          type="password"
          label="Подтвердите пароль"
          placeholder="Повторите пароль"
          minlength="6"
        ></md-outlined-text-field>
        
        <md-filled-button type="submit" @click="handleRegister">
          Зарегистрироваться
        </md-filled-button>
      </form>
      
      <p class="auth-link">
        Уже есть аккаунт? 
        <router-link to="/">Войти</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import '@material/web/textfield/outlined-text-field.js'
import '@material/web/button/filled-button.js'

const router = useRouter()

const name = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')

const handleRegister = () => {
  if (password.value !== confirmPassword.value) {
    alert('Пароли не совпадают!')
    return
  }
  
  console.log('Register attempt:', { name: name.value, email: email.value })
  router.push('/')
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(135deg, var(--md-sys-color-primary-container) 0%, var(--md-sys-color-surface) 100%);
}

.auth-card {
  background: var(--md-sys-color-surface);
  border-radius: 28px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
}

.logo {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  font-size: 56px;
  display: block;
  margin-bottom: 16px;
}

.logo h1 {
  font-size: 24px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface);
  margin: 0;
}

form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

md-outlined-text-field {
  width: 100%;
}

md-filled-button {
  width: 100%;
  margin-top: 8px;
}

.auth-link {
  text-align: center;
  margin-top: 24px;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 14px;
}

.auth-link a {
  color: var(--md-sys-color-primary);
  text-decoration: none;
  font-weight: 500;
}

.auth-link a:hover {
  text-decoration: underline;
}
</style>
