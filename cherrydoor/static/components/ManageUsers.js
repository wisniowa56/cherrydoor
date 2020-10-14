const ManageUsers = {
	data() {
		return {
			users: [],
			available_permissions: this.user.permissions,
			new_user: {
				username: "",
				password: "",
				permissions: Object.keys(this.user.permissions).reduce(
					(obj, permission) => {
						obj[permission] = false;
						if (permission == "enter") obj["enter"] = true;
						return obj;
					},
					{}
				),
				cards: [],
				password: "",
			},
			original_users: [],
		};
	},
	inject: ["user", "socket"],
	mounted() {
		this.socket.on("users", (data) => {
			if (data != null) {
				this.$data.original_users = JSON.parse(JSON.stringify(data.users));
				data.users.forEach((user) => {
					user.edit = {
						permissions: false,
						cards: user.cards.map((x) => false),
						username: false,
					};
				});
				this.$data.users = data.users;
			}
		});
		this.socket.emit("enter_room", { room: "users" });
	},
	methods: {
		addUser() {
			this.$data.users.push({
				username: this.$data.new_user.username,
				permissions: JSON.parse(
					JSON.stringify(this.$data.new_user.permissions)
				),
				cards: this.$data.new_user.cards.slice(),
				password: this.$data.new_user.password,
				edit: { permissions: false, cards: [false], username: false },
			});
			this.$data.new_user = {
				username: "",
				permissions: [],
				cards: [],
				password: "",
			};
		},
		submitUsers() {
			const original_users = this.$data.original_users;
			function difference(a, b) {
				a = new Set(a);
				b = new Set(b);
				return new Set([...a].filter((x) => !b.has(x)));
			}
			const changed_users = this.$data.users
				.slice(0, original_users.length)
				.map((user, i) => {
					if (user.username !== original_users[i].username) {
						user.current_username = original_users[i].username;
					}
					return user;
				})
				.filter((user, i) => {
					if (
						user.username === original_users[i].username &&
						difference(
							Object.values(user.permissions),
							Object.values(original_users[i].permissions)
						).size === 0 &&
						difference(user.cards, original_users[i].cards).size === 0
					) {
						return false;
					}
					return true;
				});
			this.socket.emit("modify_users", { users: changed_users });

			const new_users = this.$data.users.slice(original_users.length);
			this.socket.emit("create_users", { users: new_users });
		},
		getCard(userIndex, cardIndex) {
			this.socket.emit("get_card", (data) => {
				if (userIndex === null) {
					this.$data.new_user.cards[cardIndex] = data.uid;
				} else {
					this.$data.users[userIndex].cards[cardIndex] = data.uid;
				}
			});
		},
		deleteUser(username) {
			if (confirm(`czy na pewno chcesz usunąć użytkownika ${username}?`)) {
				this.socket.emit("delete_user", { username: username });
			}
		},
		addCard(index = null) {
			if (index === null) {
				this.$data.new_user.cards.push("");
			} else {
				this.$data.users[index].cards.push("");
				this.$data.users[index].edit.cards.push(true);
			}
		},
	},
	template: `
	<ul class="manage-users">
	<li class="user" v-for="(usr, i) in users" :key="i">
		<div class="input-editable">
			<input
				class="username existing-user"
				v-model="usr.username"
				:disabled="!usr.edit.username"
			/>
			<button
				@click="usr.edit.username = true"
				class="edit-button edit-username btn waves-effect waves-light right"
				v-if="!usr.edit.username"
			>
				Edit
			</button>
		</div>
		<div class="user-permissions existing-user" v-if="usr.permissions!=undefined">
			<div
				class="page__checkbox input-field"
				v-for="(has_permission, permission, index) in usr.permissions"
			>
				<label class="checkbox">
					<input
						type="checkbox"
						:name="permission"
						:id="permission+i"
						:aria-label="permission"
						class="checkbox-input"
						v-model="has_permission"
						:disabled="!usr.edit.permissions"
					/>
					<span class="checkbox-label">
						<span class="checkbox-text">{{permission}}</span>
					</span>
				</label>
			</div>
			<button
			class="edit-button edit-permissions btn waves-effect waves-light right"
			@click="usr.edit.permissions = true"
			v-if="!usr.edit.permissions"
		>
			Edit permissions
		</button>
		</div>

		<ul class="user-cards existing-user">
			<li v-for="(card, index) in usr.cards">
				<div class="input-editable">
					<input
						class="card-uid existing-user"
						v-model="usr.cards[index]"
						:disabled="!usr.edit.cards[index]"
					/>
					<button
						class="edit-button edit-card btn waves-effect waves-light right"
						@click="usr.edit.cards[index]=true"
						aria-label="Edit card"
						v-if="!usr.edit.cards[index]"
					>
						Edit</button>
					<button
						class="edit-button reader-input btn waves-effect waves-light"
						@click="getCard(i, index)"
						aria-label="Get card from reader"
					>
						Get card from reader
					</button>
				</div>
			</li>
			<li>
				<button class="new-card plus-button" @click="addCard(i)">Add card</button>
			</li>
		</ul>
		<button
						class="delete-button btn waves-effect waves-light"
						@click="deleteUser(usr.username)"
						aria-label="Delete user"
					>
						Delete user
					</button>
	</li>
	<li class="user new-user">
		<h3>Nowy użytkownik</h3>
		<label for="new-user-username">Nazwa użytkownika:</label>
		<input class="username new-user" v-model="new_user.username" id="new-user-username" />
		<label for="new-user-password">Hasło: <br/> <small>opcjonalne - konieczne tylko do logowania do panelu</small></label>
		<input type="password" class="password new-user" v-model="new_user.password" id="new-user-password" />
		<div class="user-permissions new-user">
			<div
				class="page__checkbox input-field"
				v-for="(has_permission, permission) in available_permissions"
			>
				<label class="checkbox" v-if="has_permission">
					<input
						type="checkbox"
						:name="permission"
						:aria-label="permission"
						class="checkbox-input"
						v-model="new_user.permissions[permission]"
					/>
					<span class="checkbox-label">
						<span class="checkbox-text">{{permission}}</span>
					</span>
				</label>
			</div>
		</div>
		<ul class="user-cards new-user">
			<li v-for="(card, index) in new_user.cards">
			<div class="input-editable">
				<input
					class="card-uid new-user"
					v-model="new_user.cards[index]"
				/>
				<button
					class="edit-button reader-input btn waves-effect waves-light"
					@click="getCard(null, index)"
					aria-label="Get card from reader"
				>
				Get card from reader
			</button>
		</div>
			</li>
			<li>
				<button class="new-card plus-button" @click="addCard()">Add card</button>
			</li>
		</ul>
		<button class="new-user plus-button" @click="addUser()">Add user</button>
	</li>
	<li>
		<button class="submit-user btn" @click="submitUsers()">Save</button>
	</li>
</ul>
`,
};

export default ManageUsers;
