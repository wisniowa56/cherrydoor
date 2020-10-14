import { inject } from "../js/vue.js";
const NavbarTemplate = `
<nav>
	<div class="nav-button"><hamburger-menu  @click="navOpen=!navOpen" :class="{ open: navOpen }"></hamburger-menu></div>
	<div class="navlink-container" :class="{ open: navOpen }">
		<router-link to="/dashboard" v-if="user.permissions.dashboard" class="navlink" :class="{ open: navOpen }">Strona główna</router-link>
		<router-link to="/users" v-if="user.permissions.users_manage || user.permissions.users_read" class="navlink" :class="{ open: navOpen }">Użytkownicy</router-link>
		<router-link to="/settings" v-if="user.permissions.admin" class="navlink" :class="{ open: navOpen }">Ustawienia</router-link>
		<router-link to="/console" v-if="user.permissions.dashboard && user.permissions.enter" class="navlink" :class="{ open: navOpen }">Konsola</router-link>
	</div>
</nav>`;

const Navbar = {
	data() {
		return { navOpen: false };
	},
	inject: ["user"],
	template: NavbarTemplate,
};

export default Navbar;
