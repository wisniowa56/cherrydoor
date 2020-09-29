import * as Vue from "./vue-dev.js";
import { createRouter, createWebHistory } from "./vue-router.js";
import Dashboard from "../components/Dashboard.js";
import Users from "../components/Users.js";
import Header from "../components/Header.js";
import Navbar from "../components/Navbar.js";
import HamburgerMenu from "../components/HamburgerMenu.js";

import UsageChart from "../components/UsageChart.js";
import DoorStatus from "../components/DoorStatus.js";
import ManageUsers from "../components/ManageUsers.js";

const socket = io();

const App = {
	data() {
		return {};
	},
	provide() {
		return { user, socket };
	},
};

const Cards = {};
const Console = {};
const User = {};

const app = Vue.createApp(App);

app.component("navbar", Navbar);
app.component("header-bar", Header);
app.component("hamburger-menu", HamburgerMenu);
app.component("usage-chart", UsageChart);
app.component("door-status", DoorStatus);
app.component("manage-users", ManageUsers);

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
			path: "/cards",
			name: "cards",
			component: Cards,
		},
		{
			path: "/console",
			name: "console",
			component: Console,
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
