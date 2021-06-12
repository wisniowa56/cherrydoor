import * as Vue from "./vue-dev.js";
import { createRouter, createWebHistory } from "./vue-router.js";
import Dashboard from "../components/Dashboard.js";
import Users from "../components/Users.js";
import SerialConsole from "../components/SerialConsole.js";
import Header from "../components/Header.js";
import Navbar from "../components/Navbar.js";
import HamburgerMenu from "../components/HamburgerMenu.js";

import UsageChart from "../components/UsageChart.js";
import DoorStatus from "../components/DoorStatus.js";
import ManageUsers from "../components/ManageUsers.js";
import Settings from "../components/Settings.js";
import vShell from "../components/v-shell.js";

const socket = io();
const App = {
	data() {
		return {};
	},
	provide() {
		return { user, socket };
	},
};

const User = {};

const app = Vue.createApp(App);
app.mixin({
	methods: {
		ObjEqual(a, b) {
			if (a === b) return true;
			if (!(a instanceof Object) || !(b instanceof Object)) return false;

			var keys = keyList(a);
			var length = keys.length;

			for (var i = 0; i < length; i++) if (!(keys[i] in b)) return false;

			for (var i = 0; i < length; i++)
				if (a[keys[i]] !== b[keys[i]]) return false;

			return length === keyList(b).length;
		},
	},
});

app.component("navbar", Navbar);
app.component("header-bar", Header);
app.component("hamburger-menu", HamburgerMenu);
app.component("usage-chart", UsageChart);
app.component("door-status", DoorStatus);
app.component("manage-users", ManageUsers);
app.component("v-shell", vShell);

const router = createRouter({
	history: createWebHistory(),
	routes: [
		{
			path: "/dashboard",
			name: "dashboard",
			alias: "/",
			component: Dashboard,
		},
		{
			path: "/users",
			name: "users",
			component: Users,
		},
		{
			path: "/settings",
			name: "settings",
			component: Settings,
		},
		{
			path: "/console",
			name: "console",
			component: SerialConsole,
		},
		{
			path: "/user",
			name: "user",
			component: User,
		},
	],
});
app.use(router);

app.mount("#app");
